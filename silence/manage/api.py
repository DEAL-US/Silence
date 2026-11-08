import json
import os
import re

import pymysql
from flask import Blueprint, jsonify, request, current_app

from silence import __version__
from silence.auth.passwords import password_status, hash_password
from silence.db import dal, schema as db_schema
from silence.db.connector import test_connection
from silence.db.errors import to_http_error
from silence.exceptions import HTTPError, DatabaseError
from silence.settings import settings, PROJECT_FILE
from silence.server import watcher
from silence.server.endpoints import REGISTRY, AUTO_PREFIX, Endpoint
from silence.server.session import get_field
from silence.project.files import read_json, etag_of, safe_name
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


def endpoint_dict(e):
    d = e.to_dict()
    d["file"] = d["file"].removesuffix(".json")
    return d


@manage.route("/status")
def status():
    '''State of the project: database, users, the endpoints that are being served, tests, errors and
    revision'''
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
                      "custom": sum(1 for e in REGISTRY.endpoints if e.source == "custom"),
                      "list": [endpoint_dict(e) for e in REGISTRY.endpoints]},
        "tests": {"custom": len(suite.tests)},
        "errors": {"config": settings.errors + scripts_missing(), "endpoints": REGISTRY.errors, "tests": suite.errors},
    })


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
    from silence.auth import users as users_table
    rel = users_rel()
    a = settings.USER_AUTH_DATA
    try:
        rows = dal.query(f"{users_table.users_select()} ORDER BY u.`{rel.single_pk}` LIMIT 1000")
    except users_table.UsersTableError as exc:
        raise HTTPError(409, f"The users table is not well linked: {exc}")
    except DatabaseError as exc:
        raise to_http_error(exc)
    def user(r):
        stored = get_field(r, a["password"])
        status = password_status(stored)
        return {"id": r[rel.single_pk], "identifier": get_field(r, users_table.identifier_field()),
                "role": get_field(r, a["role"]) if a["role"] else None,
                "active": get_field(r, a["active_status"]) if a["active_status"] else None,
                "password": status,
                # Stored as plain text (in plain mode, for practice databases): shown, to try the login
                "plainPassword": stored if settings.PASSWORD_MODE == "plain" and status == "plain" else None}
    users = [user(r) for r in rows]
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
    from silence.auth import users as users_table
    rows = dal.query(f"{users_table.users_select()} WHERE u.`{rel.single_pk}` = %s", (user_id,))
    if not rows:
        raise HTTPError(404, "No such user")
    return jsonify(session_for(rows[0]))


###############################################################################
# Generation: the endpoints from the schema, and the tests from the
# endpoints and the data (they are not files: computed when asked for)
###############################################################################

@manage.route("/endpoints/generate", methods=["POST"])
def generate_endpoints():
    '''Generates the autogenerated endpoints and the JS API (as silence createapi)'''
    from silence.server import generator
    require_db()
    try:
        res = generator.generate(body().get("tables") or None)
    except ValueError as exc:
        raise HTTPError(400, str(exc))
    watcher.bump()
    return jsonify(res)


@manage.route("/tests/generated")
def generated_tests():
    '''The generated tests, computed now from the endpoints and the data of the database
    (the custom ones are the files tests/*.json)'''
    from silence.testing.generator import generated_tests as generate
    require_db()
    try:
        tests = generate()
    except DatabaseError as exc:
        raise to_http_error(exc)
    res = []
    for t in tests:
        d = t.to_dict()
        d["file"] = d["file"].removesuffix(".json")
        res.append(d)
    return jsonify({"tests": res})


###############################################################################
# The files of the project: silence.json, endpoints/*.json, tests/*.json and
# the log of requests (admin/logs/requests.log). Each one is checked as what it
# is before saving it; the rest of the project is not reachable.
###############################################################################

NAME = r"[A-Za-z0-9_-]+"
FILES = [  # (pattern, kind, folder that is listed)
    (re.compile(r"silence\.json"), "config", None),
    (re.compile(rf"endpoints/{NAME}\.json"), "endpoints", "endpoints"),
    (re.compile(rf"tests/{NAME}\.json"), "tests", "tests"),
    (re.compile(r"admin/logs/requests\.log"), "log", "admin/logs"),
]


def file_kind(path):
    for pattern, kind, _ in FILES:
        if pattern.fullmatch(path):
            return kind
    raise HTTPError(403, f"'{path}' is not a file that can be managed: silence.json, endpoints/*.json, "
                         "tests/*.json or admin/logs/requests.log")


def full_path(path):
    return os.path.join(settings.PROJECT_DIR, *path.split("/"))


def is_auto(path):
    return os.path.basename(path).startswith(AUTO_PREFIX)


def json_body():
    try:
        return json.loads(request.get_data(as_text=True))
    except ValueError:
        raise HTTPError(400, "Send the content of the file as JSON")


def entries_or_400(data, what):
    if not isinstance(data, dict):
        raise HTTPError(400, f"The file must contain an object with the {what} by name")
    for name in data:
        name_or_400(name)
    return data


def check_endpoints(path, data):
    file = os.path.basename(path)
    keys = {}
    for name, definition in entries_or_400(data, "endpoints").items():
        try:
            ep = Endpoint(name, definition, path)
        except Exception as exc:
            raise HTTPError(400, f"{name}: {exc}")
        if ep.key in keys:
            raise HTTPError(409, f"{ep.key} is defined twice in {file}: '{keys[ep.key]}' and '{name}'")
        keys[ep.key] = name
        # A custom endpoint may replace an autogenerated one, not another custom one
        clash = next((e for e in REGISTRY.endpoints if e.key == ep.key and e.source == "custom"
                      and e.file != file), None)
        if clash:
            raise HTTPError(409, f"{ep.key} is already defined as '{clash.name}' in {clash.file}")


def check_tests(path, data):
    file = os.path.basename(path)
    entries = entries_or_400(data, "tests")
    for name, definition in entries.items():
        try:
            test_model.Test(name, definition, path)
        except Exception as exc:
            raise HTTPError(400, f"{name}: {exc}")
    if not entries:
        return
    generated = test_model.generated_names() & set(entries)
    if generated:
        raise HTTPError(409, f"'{sorted(generated)[0]}' is the name of a generated test: choose another one")
    clash = next((t for t in test_model.load_tests().tests if t.name in entries and t.file != file), None)
    if clash:
        raise HTTPError(409, f"There is already a test '{clash.name}' in {clash.file}")


def save_config(data):
    '''silence.json: checked, and its connection tried, before saving it; the secret key is kept'''
    from silence.db import scripts
    if not isinstance(data, dict):
        raise HTTPError(400, "silence.json must contain an object")
    db = data.get("database") if isinstance(data.get("database"), dict) else {}
    listed = db.get("scripts")
    if isinstance(listed, list):
        absent = scripts.missing([s for s in listed if isinstance(s, str)])
        if absent:
            raise HTTPError(400, f"Not saved: there is no {', '.join('sql/' + s for s in absent)} in the project")
    old = settings.project
    conn = ("host", "port", "user", "password", "name")
    if any(db.get(k, old["database"][k]) != old["database"][k] for k in conn) and db.get("name"):
        new = {**old["database"], **db}
        error = test_connection({"host": new["host"], "port": new["port"], "username": new["user"],
                                 "password": new["password"], "database": new["name"]})
        if error:
            raise HTTPError(400, f"Not saved: cannot connect: {error}")
    old_server = dict(old["server"])
    try:
        settings.replace(data)
    except ValueError as exc:
        raise HTTPError(400, f"Not saved: {exc}")
    db_schema.invalidate()
    REGISTRY.load()
    server = settings.project["server"]
    return {"restartNeeded": any(server[k] != old_server[k] for k in ("address", "port"))}


@manage.route("/files")
def list_files():
    '''The files that can be managed, with their versions (only those of a folder with ?dir=)'''
    folder = request.args.get("dir")
    folders = [f for _, _, f in FILES if f]
    if folder is not None and folder not in folders:
        raise HTTPError(400, f"dir must be one of: {', '.join(folders)}")
    res = []
    if folder is None and os.path.isfile(settings.PROJECT_PATH):
        res.append({"path": PROJECT_FILE, "etag": etag_of(settings.PROJECT_PATH)})
    for f in [folder] if folder else folders:
        where = full_path(f)
        if os.path.isdir(where):
            for name in sorted(os.listdir(where)):
                rel = f"{f}/{name}"
                if any(p.fullmatch(rel) for p, _, _ in FILES) and os.path.isfile(os.path.join(where, name)):
                    res.append({"path": rel, "etag": etag_of(os.path.join(where, name))})
    return jsonify({"files": res})


@manage.route("/files/<path:path>")
def get_file(path):
    '''A file: its content (JSON, or the text of the log) and its version; null if it does not exist'''
    kind = file_kind(path)
    where = full_path(path)
    if kind == "config":
        data = {k: v for k, v in settings.project.items() if k != "secret_key"}
    elif not os.path.isfile(where):
        data = None
    elif kind == "log":
        with open(where, encoding="utf8", errors="replace") as f:
            data = f.read()
    else:
        try:
            data = read_json(where)
        except ValueError as exc:
            raise HTTPError(409, f"{path} is not valid JSON: {exc}")
    return jsonify({"path": path, "data": data, "etag": etag_of(where)})


@manage.route("/files/<path:path>", methods=["PUT"])
def put_file(path):
    '''Saves a file (all of it), after checking it as what it is'''
    kind = file_kind(path)
    where = full_path(path)
    if kind == "log":
        raise HTTPError(403, "The log is written by Silence: it can only be read or deleted")
    if kind in ("endpoints", "tests") and is_auto(path):
        raise HTTPError(403, f"{path} is autogenerated: write the custom file of the table, whose "
                             "endpoints replace the autogenerated ones with the same method and route")
    check_if_match(where)
    data = json_body()
    created = not os.path.isfile(where)
    extra = {}
    if kind == "config":
        extra = save_config(data)
    else:
        if kind == "endpoints":
            check_endpoints(where, data)
        elif kind == "tests":
            check_tests(where, data)
        os.makedirs(os.path.dirname(where), exist_ok=True)
        with open(where, "w", encoding="utf8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        if kind == "endpoints":
            REGISTRY.load()
    watcher.bump()
    return jsonify({"path": path, "etag": etag_of(where), **extra}), 201 if created else 200


@manage.route("/files/<path:path>", methods=["DELETE"])
def delete_file(path):
    '''Deletes a file (the log: resets the console and the statistics of the panel)'''
    kind = file_kind(path)
    where = full_path(path)
    if kind == "config":
        raise HTTPError(403, "silence.json cannot be deleted")
    if kind in ("endpoints", "tests") and is_auto(path):
        raise HTTPError(403, f"{path} is autogenerated: generate the endpoints again instead")
    check_if_match(where)
    if not os.path.isfile(where):
        raise HTTPError(404, f"There is no {path}")
    os.remove(where)
    if kind == "endpoints":
        REGISTRY.load()
    if kind in ("endpoints", "tests"):
        watcher.bump()
    return jsonify({"deleted": True})

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
            status = "201" if op_id == "put_file" else "200"
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
