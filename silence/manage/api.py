import json
import os
import re

import pymysql
from flask import Blueprint, jsonify, request, current_app

from silence import __version__
from silence.auth.passwords import password_status, hash_password, is_argon2
from silence.db import dal, schema as db_schema
from silence.db.connector import test_connection
from silence.db.errors import to_http_error
from silence.exceptions import HTTPError, DatabaseError
from silence.settings import settings, PROJECT_FILE
from silence.server import stats, watcher
from silence.server.endpoints import REGISTRY, endpoints_dir, AUTO_PREFIX, route_key, Endpoint
from silence.server.session import get_field
from silence.project.files import read_json, write_json, etag_of, etags, safe_name
from silence.testing import model as test_model
from silence.manage import schemas

###############################################################################
# Admin API (/_silence/v1): the operations to administer Silence itself.
# It is the contract used by the admin panel (silence-admin-panel), and the
# CLI runs the same code. Only reachable from this computer. See
# docs/admin-api.md.
###############################################################################

API_VERSION = 1
PREFIX = f"/_silence/v{API_VERSION}"
manage = Blueprint("manage", __name__, url_prefix=PREFIX)

CONFIG_SECTIONS = ("server", "database", "auth", "js_api", "debug")


@manage.before_request
def only_local():
    if request.remote_addr not in ("127.0.0.1", "::1", None):
        raise HTTPError(403, "The admin API can only be used from this computer")


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def db_ok():
    return bool(settings.DB_CONN["database"]) and test_connection(settings.DB_CONN) is None


def require_db():
    if not db_ok():
        raise HTTPError(409, "The database is not configured or not reachable")


def check_if_match(path):
    '''412 if the client sent If-Match with another version of the file'''
    expected = request.headers.get("If-Match")
    if expected is not None and expected.strip('"') != etag_of(path):
        raise HTTPError(412, f"{os.path.relpath(path, settings.PROJECT_DIR)} has changed since you read it: "
                             "reload it before saving")


def name_or_400(name):
    try:
        return safe_name(name)
    except ValueError as exc:
        raise HTTPError(400, str(exc))


###############################################################################
# Silence and the project
###############################################################################

@manage.route("/")
def root():
    '''Versions of Silence and of this API, the project, and how to call the student's API'''
    return jsonify({"silence": __version__, "api": API_VERSION,
                    "project": os.path.basename(settings.PROJECT_DIR), "projectDir": settings.PROJECT_DIR,
                    # What a client (the admin panel) needs to call the student's API
                    "studentApi": {"prefix": settings.API_PREFIX, "sessionHeader": "Token"}})


def scripts_missing():
    '''database.scripts that are not in sql/ (e.g., silence.json edited by hand, or a script deleted)'''
    from silence.db import scripts
    absent = scripts.missing(settings.project["database"].get("scripts") or [])
    return [f"database.scripts: there is no sql/{s}" for s in absent]


@manage.route("/status")
def status():
    '''State of the project: database, users, endpoints, tests, errors and revision'''
    db_error = test_connection(settings.DB_CONN) if settings.DB_CONN["database"] else "no database selected"
    suite = test_model.load_tests()  # The custom ones: generating the others takes a while
    return jsonify({
        "revision": watcher.revision(),
        "apiPrefix": settings.API_PREFIX,
        "baseUrl": f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}",
        "database": {"name": settings.DB_CONN["database"], "error": db_error},
        "auth": {"linked": settings.AUTH_LINKED, **settings.project["auth"]},
        "endpoints": {"count": len(REGISTRY.endpoints),
                      "auto": sum(1 for e in REGISTRY.endpoints if e.source == "auto"),
                      "custom": sum(1 for e in REGISTRY.endpoints if e.source == "custom")},
        "tests": {"custom": len(suite.tests)},
        "errors": {"config": settings.errors + scripts_missing(), "endpoints": REGISTRY.errors, "tests": suite.errors},
    })


###############################################################################
# Configuration (silence.json)
###############################################################################

@manage.route("/config")
def get_config():
    '''silence.json, without the secret key'''
    data = {k: v for k, v in settings.project.items() if k != "secret_key"}
    return jsonify({"config": data, "etag": etag_of(settings.PROJECT_PATH)})


@manage.route("/config/<section>", methods=["PATCH"])
def patch_config(section):
    '''Changes some values of a section (server, database, auth, js_api or debug)'''
    if section not in CONFIG_SECTIONS:
        raise HTTPError(404, f"Unknown section '{section}'")
    check_if_match(settings.PROJECT_PATH)
    values = request.get_json(silent=True)
    if section == "debug":
        if not isinstance(values, dict) or "debug" not in values:
            raise HTTPError(400, "Send {\"debug\": true|false}")
        values = bool(values["debug"])
    elif not isinstance(values, dict):
        raise HTTPError(400, "Send an object with the values to change")
    if section == "database" and isinstance(values.get("scripts"), list):
        from silence.db import scripts
        absent = scripts.missing([s for s in values["scripts"] if isinstance(s, str)])
        if absent:
            raise HTTPError(400, f"Not saved: there is no {', '.join('sql/' + s for s in absent)} in the project")
    if section == "database" and set(values) - {"scripts"}:
        new = {**settings.project["database"], **values}
        error = test_connection({"host": new["host"], "port": new["port"], "username": new["user"],
                                 "password": new["password"], "database": new["name"]})
        if error:
            raise HTTPError(400, f"Cannot connect: {error}")
    try:
        settings.update(section, values)
    except ValueError as exc:
        raise HTTPError(400, f"Not saved: {exc}")
    db_schema.invalidate()
    REGISTRY.load()
    watcher.bump()
    restart = section == "server" and any(k in values for k in ("address", "port"))
    return jsonify({"restartNeeded": restart, "etag": etag_of(settings.PROJECT_PATH)})


###############################################################################
# Database
###############################################################################

def connection_args(v):
    return {"host": v.get("host"), "port": int(v.get("port") or 3306), "username": v.get("user"),
            "password": v.get("password"), "database": v.get("name") or None}


@manage.route("/database/test", methods=["POST"])
def database_test():
    '''Tries a connection without saving it; if the user can connect, also the databases it sees'''
    a = connection_args(body())
    try:
        conn = pymysql.connect(host=a["host"], port=a["port"], user=a["username"], password=a["password"],
                               connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES")
            names = [r[0] for r in cur.fetchall()
                     if r[0] not in ("information_schema", "mysql", "performance_schema", "sys")]
        conn.close()
    except pymysql.MySQLError as exc:
        return jsonify({"ok": False, "error": exc.args[1] if len(exc.args) > 1 else str(exc), "databases": []})
    error = test_connection(a) if a["database"] else None
    if error is None and a["database"] and a["database"] not in names:
        error = f"There is no database '{a['database']}' (or this user cannot see it)"
    return jsonify({"ok": error is None, "error": error, "databases": names})


@manage.route("/database/reload", methods=["POST"])
def database_reload():
    '''Creates the database again with the scripts of database.scripts, in order, as silence createdb
    of Silence 2 (e.g., to run the tests again from the original data)'''
    from silence.db import scripts
    require_db()
    if not settings.project["database"].get("scripts"):
        raise HTTPError(409, "Choose the scripts that reload the database first (database.scripts)")
    try:
        done = scripts.reload()
    except scripts.ScriptError as exc:
        db_schema.invalidate()
        return jsonify({"code": 400, "message": str(exc), "file": exc.file, "line": exc.line,
                        "statement": exc.statement[:2000]}), 400
    db_schema.invalidate()
    REGISTRY.load()
    return jsonify({"scripts": done})


@manage.route("/schema")
def get_schema():
    '''Tables and views of the database, with their columns, keys and number of rows'''
    require_db()
    data = db_schema.get_schema(refresh=True).to_dict()
    for rel in data["relations"]:
        try:
            rel["rows"] = dal.query(f"SELECT COUNT(*) AS n FROM `{rel['name']}`")[0]["n"]
        except DatabaseError:
            rel["rows"] = None  # E.g., a view that no longer works
    return jsonify(data)


###############################################################################
# Users
###############################################################################

def users_rel():
    if not settings.AUTH_LINKED:
        raise HTTPError(409, "The users table is not linked")
    require_db()
    rel = db_schema.get_schema().get(settings.USER_AUTH_DATA["table"])
    if rel is None or rel.single_pk is None:
        raise HTTPError(409, "The users table does not exist or has no single primary key")
    return rel


@manage.route("/users")
def list_users():
    '''The users, with the state of their password (never its value)'''
    rel = users_rel()
    a = settings.USER_AUTH_DATA
    try:
        rows = dal.query(f"SELECT * FROM {rel.name} ORDER BY {rel.single_pk} LIMIT 1000")
    except DatabaseError as exc:
        raise to_http_error(exc)
    users = [{"id": r[rel.single_pk], "identifier": get_field(r, a["identifier"]),
              "role": get_field(r, a["role"]) if a["role"] else None,
              "active": get_field(r, a["active_status"]) if a["active_status"] else None,
              "password": password_status(get_field(r, a["password"]))} for r in rows]
    return jsonify({"pk": rel.single_pk, "passwordMode": settings.PASSWORD_MODE, "users": users})


def store_password(rel, password, user_id=None):
    col = rel.column(settings.USER_AUTH_DATA["password"]).name
    where, params = (f" WHERE {rel.single_pk} = %s", (user_id,)) if user_id is not None else ("", ())
    ids = [r[rel.single_pk] for r in dal.query(f"SELECT {rel.single_pk} FROM {rel.name}{where}", params)]
    for uid in ids:  # One hash per user (each one with its own salt)
        dal.update(f"UPDATE {rel.name} SET {col} = %s WHERE {rel.single_pk} = %s", (hash_password(password), uid))
    return len(ids)


@manage.route("/users/<user_id>/password", methods=["PUT"])
def set_password(user_id):
    '''Sets the password of a user (encrypted or not, as the project says)'''
    rel = users_rel()
    password = body().get("password")
    if not password:
        raise HTTPError(400, "The password cannot be empty")
    if store_password(rel, password, user_id) == 0:
        raise HTTPError(404, "No such user")
    return jsonify({"updated": 1})


@manage.route("/users/<user_id>/session", methods=["POST"])
def user_session(user_id):
    '''Opens a session for a user without its password'''
    from silence.server.auth_endpoints import session_for
    rel = users_rel()
    rows = dal.query(f"SELECT * FROM {rel.name} WHERE {rel.single_pk} = %s", (user_id,))
    if not rows:
        raise HTTPError(404, "No such user")
    return jsonify(session_for(rows[0]))


@manage.route("/hash", methods=["POST"])
def hash_value():
    '''The argon2 hash of a password (as silence hash)'''
    from silence.auth.passwords import _hasher
    password = body().get("password")
    if not password:
        raise HTTPError(400, "The password cannot be empty")
    return jsonify({"hash": _hasher.hash(password)})


###############################################################################
# Endpoints and tests: files as resources (/{kind}/{file}/{name})
###############################################################################

class Kind:
    '''What changes between endpoints and tests'''
    def __init__(self, name, folder, validate, load, generate):
        self.name, self.folder, self.validate, self.load, self.generate = name, folder, validate, load, generate

    def path(self, file):
        return os.path.join(self.folder(), f"{file}.json")


def validate_endpoint(name, data, path):
    ep = Endpoint(name, data, path)
    # A custom endpoint may replace an autogenerated one, not another custom one
    clash = next((e for e in REGISTRY.endpoints if e.key == ep.key and e.source == "custom"
                  and not (e.file == os.path.basename(path) and e.name == name)), None)
    if clash:
        raise HTTPError(409, f"{ep.key} is already defined as '{clash.name}' in {clash.file}")


def validate_test(name, data, path):
    test_model.Test(name, data, path)
    clash = next((t for t in test_model.load_tests().tests
                  if t.name == name and t.file != os.path.basename(path)), None)
    if clash:
        raise HTTPError(409, f"There is already a test '{name}' in {clash.file}")


def generate_endpoints(tables):
    from silence.server import generator
    return generator.generate(tables)


ENDPOINTS = Kind("endpoint", endpoints_dir, validate_endpoint, REGISTRY.load, generate_endpoints)
TESTS = Kind("test", test_model.tests_dir, validate_test, lambda: None, None)


def get_entry(kind, file, name):
    file, name = name_or_400(file), name_or_400(name)
    content = read_json(kind.path(file))
    if name not in content:
        raise HTTPError(404, f"There is no {kind.name} '{name}' in {file}.json")
    return jsonify({"file": file, "name": name, "data": content[name], "etag": etag_of(kind.path(file))})


def put_entry(kind, file, name):
    file, name = name_or_400(file), name_or_400(name)
    if file.startswith(AUTO_PREFIX):
        raise HTTPError(400, f"Autogenerated {kind.name}s are not edited: customize it first")
    path = kind.path(file)
    check_if_match(path)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise HTTPError(400, f"Send the {kind.name} as an object")
    try:
        kind.validate(name, data, path)
    except HTTPError:
        raise
    except Exception as exc:
        raise HTTPError(400, str(exc))
    content = read_json(path)
    created = name not in content
    content[name] = data
    etag = write_json(path, content)
    kind.load()
    watcher.bump()
    return jsonify({"file": file, "name": name, "etag": etag}), 201 if created else 200


def delete_entry(kind, file, name):
    file, name = name_or_400(file), name_or_400(name)
    if file.startswith(AUTO_PREFIX):
        raise HTTPError(400, f"Autogenerated {kind.name}s are removed by generating them again")
    path = kind.path(file)
    check_if_match(path)
    content = read_json(path)
    if content.pop(name, None) is None:
        raise HTTPError(404, f"There is no {kind.name} '{name}' in {file}.json")
    etag = write_json(path, content)
    kind.load()
    watcher.bump()
    return jsonify({"deleted": True, "etag": etag})


def customize_entry(kind, file, name):
    file, name = name_or_400(file), name_or_400(name)
    if not file.startswith(AUTO_PREFIX):
        raise HTTPError(400, f"Only autogenerated {kind.name}s are customized")
    auto_path = kind.path(file)
    table = file[len(AUTO_PREFIX):]
    custom_path = kind.path(table)
    auto, custom = read_json(auto_path), read_json(custom_path)
    if name not in auto:
        raise HTTPError(404, f"There is no {kind.name} '{name}' in {file}.json")
    new_name = name if name not in custom else f"{name}_custom"
    custom[new_name] = auto.pop(name)
    write_json(custom_path, custom)
    write_json(auto_path, auto)
    kind.load()
    watcher.bump()
    return jsonify({"file": table, "name": new_name})


@manage.route("/endpoints")
def list_endpoints():
    '''All the endpoints, the files with their versions and the loading errors'''
    REGISTRY.load()
    eps = []
    for e in REGISTRY.endpoints:
        d = e.to_dict()
        d["file"] = d["file"].removesuffix(".json")
        eps.append(d)
    return jsonify({"endpoints": eps, "files": etags(endpoints_dir()), "errors": REGISTRY.errors,
                    "apiPrefix": settings.API_PREFIX})


@manage.route("/endpoints/<file>/<name>")
def get_endpoint(file, name):
    '''An endpoint'''
    return get_entry(ENDPOINTS, file, name)


@manage.route("/endpoints/<file>/<name>", methods=["PUT"])
def put_endpoint(file, name):
    '''Creates or replaces a custom endpoint'''
    return put_entry(ENDPOINTS, file, name)


@manage.route("/endpoints/<file>/<name>", methods=["DELETE"])
def delete_endpoint(file, name):
    '''Deletes a custom endpoint'''
    return delete_entry(ENDPOINTS, file, name)


@manage.route("/endpoints/<file>/<name>/customize", methods=["POST"])
def customize_endpoint(file, name):
    '''Moves an autogenerated endpoint to the custom file of its table'''
    return customize_entry(ENDPOINTS, file, name)


@manage.route("/endpoints/generate", methods=["POST"])
def generate_endpoints_route():
    '''Generates the autogenerated endpoints and the JS API (as silence createapi)'''
    require_db()
    try:
        res = generate_endpoints(body().get("tables") or None)
    except ValueError as exc:
        raise HTTPError(400, str(exc))
    watcher.bump()
    return jsonify(res)


@manage.route("/tests")
def list_tests():
    '''All the tests (the generated ones, computed now, and the custom ones, which replace the
    generated ones with their name), the versions of the custom files and the loading errors'''
    suite = test_model.all_tests() if db_ok() else test_model.load_tests()
    tests = []
    for t in suite.tests:
        d = t.to_dict()
        d["file"] = d["file"].removesuffix(".json")
        tests.append(d)
    return jsonify({"tests": tests, "files": etags(test_model.tests_dir()), "errors": suite.errors})


@manage.route("/tests/<file>/<name>")
def get_test(file, name):
    '''A test'''
    return get_entry(TESTS, file, name)


@manage.route("/tests/<file>/<name>", methods=["PUT"])
def put_test(file, name):
    '''Creates or replaces a custom test'''
    return put_entry(TESTS, file, name)


@manage.route("/tests/<file>/<name>", methods=["DELETE"])
def delete_test(file, name):
    '''Deletes a custom test (if it replaced a generated one, the generated one is seen again)'''
    return delete_entry(TESTS, file, name)


###############################################################################
# The admin panel's own data (e.g., its composite tests), in the project's
# admin/data/<name>.json. Silence stores it without knowing what it is.
###############################################################################

def panel_data_path(name):
    return os.path.join(settings.PROJECT_DIR, "admin", "data", f"{name_or_400(name)}.json")


@manage.route("/panel-data/<name>")
def get_panel_data(name):
    '''Data saved by the admin panel (null if there is none)'''
    path = panel_data_path(name)
    data = read_json(path) if os.path.isfile(path) else None
    return jsonify({"name": name, "data": data, "etag": etag_of(path)})


@manage.route("/panel-data/<name>", methods=["PUT"])
def put_panel_data(name):
    '''Saves data of the admin panel (any JSON), in admin/data/<name>.json'''
    path = panel_data_path(name)
    check_if_match(path)
    data = request.get_json(silent=True)
    if data is None:
        raise HTTPError(400, "Send the data as JSON")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")
    return jsonify({"name": name, "etag": etag_of(path)})


###############################################################################
# Statistics
###############################################################################

@manage.route("/stats")
def get_stats():
    '''Requests since Silence started: the student's API, Silence's API and the web app'''
    return jsonify(stats.snapshot())


@manage.route("/stats", methods=["DELETE"])
def reset_stats():
    '''Resets the statistics'''
    stats.reset()
    return jsonify({"reset": True})


###############################################################################
# OpenAPI, built from the routes of this blueprint and their docstrings
###############################################################################

@manage.route("/openapi.json")
def openapi():
    '''This specification'''
    paths = {}
    for rule in current_app.url_map.iter_rules():
        if not rule.rule.startswith(PREFIX) or rule.endpoint == "manage.openapi":
            continue
        path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule[len(PREFIX):]) or "/"
        view = current_app.view_functions[rule.endpoint]
        summary = (view.__doc__ or "").strip().splitlines()[0] if view.__doc__ else rule.endpoint
        params = [{"name": p, "in": "path", "required": True, "schema": {"type": "string"}}
                  for p in re.findall(r"\{(\w+)\}", path)]
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            op_id = rule.endpoint.split(".")[-1]
            response, request_body = schemas.OPERATIONS.get(op_id, (None, None))
            json_of = lambda schema: {"content": {"application/json": {"schema": schema}}}
            ok = {"description": "OK", **json_of(schemas.ref(response))} if response else {"description": "OK"}
            status = "201" if op_id in ("put_endpoint", "put_test") else "200"
            op = {"summary": summary, "operationId": op_id,
                  "responses": {"200": ok, **({"201": ok} if status == "201" else {}),
                                "default": {"description": "Error", **json_of(schemas.ref("Error"))}}}
            if params:
                op["parameters"] = params
            if request_body is not None:
                op["requestBody"] = json_of(request_body)
            if method in ("PUT", "PATCH", "DELETE") and op_id != "set_password":
                op.setdefault("parameters", []).append(
                    {"name": "If-Match", "in": "header", "required": False, "schema": {"type": "string"},
                     "description": "Version (etag) of the file that was read; 412 if it has changed"})
            paths.setdefault(path, {})[method.lower()] = op
    return jsonify({
        "openapi": "3.1.0",
        "info": {"title": "Silence admin API", "version": f"{API_VERSION}.0",
                 "description": "Operations to administer a Silence project (docs/admin-api.md). "
                                "Only reachable from this computer."},
        "servers": [{"url": PREFIX}],
        "paths": dict(sorted(paths.items())),
        "components": {"schemas": schemas.COMPONENTS},
    })
