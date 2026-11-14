import json
import os
import re

import pymysql
from flask import Blueprint, jsonify, request, current_app

from silence import __version__
from silence.auth.passwords import password_status, hash_password
from silence.db import dal, schema as db_schema
from silence.db.connector import get_conn, test_connection, connection_error, error_message
from silence.db.errors import to_http_error
from silence.exceptions import HTTPError, DatabaseError
from silence.settings import settings, PROJECT_FILE, DEFAULT_PROJECT, merge, db_conn_of
from silence.server.endpoints import REGISTRY, AUTO_PREFIX, Endpoint
from silence.server.session import get_field
from silence.server.auth_endpoints import session_for
from silence.auth import users as users_table
from silence.db import scripts
from silence.project.files import write_json, etag_of, read_with_etag, safe_name
from silence.testing import model as test_model
from silence.testing.generator import write_generated_tests
from silence.server import generator
from silence.manage import schemas
from silence.cli import template_downloader as tpl
from silence.project import molds
from silence.cli.commands.new import panel_version

###############################################################################
# Admin API (/_silence/v1): the operations to administer Silence itself.
# It is the contract used by the admin panel (silence-v3-admin-panel-uikit), and the
# CLI runs the same code. Only reachable from this computer. See
# docs/admin-api.md.
###############################################################################

API_VERSION = 1
PREFIX = f"/_silence/v{API_VERSION}"
manage = Blueprint("manage", __name__, url_prefix=PREFIX)

LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]")


def host_of(value):
    '''The host of a Host header ("127.0.0.1:8080") or of an Origin ("http://localhost:8080"),
    without the port'''
    host = value.split("://", 1)[-1].split("/", 1)[0].lower()
    if host.startswith("["):
        return host[:host.index("]") + 1] if "]" in host else host
    return host.split(":", 1)[0]


@manage.before_request
def only_local():
    '''Only from this computer, and only from its pages: the Host must be a local name (a page of
    another site whose name resolves to 127.0.0.1, DNS rebinding, is rejected), and a change must
    not come from a page of another site (a form of another site that posts here, CSRF)'''
    if request.remote_addr not in ("127.0.0.1", "::1"):
        raise HTTPError(403, "The admin API can only be used from this computer")
    if host_of(request.host) not in LOCAL_HOSTS:
        raise HTTPError(403, "The admin API can only be used through localhost or 127.0.0.1")
    origin = request.headers.get("Origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin is not None \
            and origin.rstrip("/") != request.host_url.rstrip("/"):
        raise HTTPError(403, "The admin API only accepts changes from the admin panel of this project")


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def db_ok():
    return connection_error() is None


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

EZ_UI = {"repo": "IISSI-US/ez-ui", "file": "web/ez-ui/VERSION.txt"}


def versions():
    '''The version of each piece of the project: Silence, the admin panel (the one in silence.json and
    the one installed in admin/), the template of the front-end and ez-ui (if the project has it)'''
    panel = panel_version(settings.PROJECT_DIR) or {}
    ez_text, _ = read_with_etag(full_path(EZ_UI["file"]))
    return {
        "silence": {"version": __version__, "adminApi": API_VERSION},
        "panel": {**(settings.project.get("admin") or {}), "installed": panel.get("version"),
                  "adminApi": panel.get("api")},
        "template": settings.project.get("template"),
        "ezUi": {"repo": EZ_UI["repo"], "version": ez_text.strip()} if ez_text else None,
    }


def latest_versions(current):
    '''The latest published version of each piece, or why it cannot be known'''
    from silence.utils.check_update import latest_version
    res = {}
    try:
        res["silence"] = {"version": latest_version()}
    except Exception as exc:
        res["silence"] = {"error": f"Cannot read PyPI: {exc}"}
    for key in ("panel", "template", "ezUi"):
        repo = (current.get(key) or {}).get("repo")
        if not repo:
            res[key] = None
            continue
        try:
            res[key] = {"version": tpl.latest_tag(repo)}
        except tpl.DownloadError as exc:
            res[key] = {"error": str(exc)}
    return res


@manage.route("/")
def root():
    '''Versions of Silence, of this API and of each piece of the project, the project, and how to call
    the student's API. With ?updates=true, also the latest published versions (it goes to the network)'''
    current = versions()
    res = {"silence": __version__, "api": API_VERSION, "versions": current,
           "project": os.path.basename(settings.PROJECT_DIR), "projectDir": settings.PROJECT_DIR,
           # What a client (the admin panel) needs to call the student's API
           "studentApi": {"prefix": settings.API_PREFIX, "sessionHeader": "Token"}}
    if request.args.get("updates") == "true":
        res["latest"] = latest_versions(current)
    return jsonify(res)


def scripts_missing():
    '''database.scripts that are not in sql/ (e.g., silence.json edited by hand, or a script deleted)'''
    absent = scripts.missing(settings.project["database"].get("scripts") or [])
    return [f"database.scripts: there is no sql/{s}" for s in absent]


def endpoint_dict(e):
    d = e.to_dict()
    d["file"] = d["file"].removesuffix(".json")
    return d


def table_count():
    '''The tables of the connected database (0: it is empty, it has to be loaded with the scripts)'''
    try:
        rows = dal.query("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = DATABASE() "
                         "AND table_type = 'BASE TABLE'")
        return int(rows[0]["n"])
    except Exception:
        return None


@manage.route("/status")
def status():
    '''State of the project: database, users, the endpoints that are being served, tests and errors'''
    db_error = connection_error()
    suite = test_model.load_tests()  # The custom ones: generating the others takes a while
    return jsonify({
        "apiPrefix": settings.API_PREFIX,
        "baseUrl": f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}",
        "database": {"name": settings.DB_CONN["database"], "error": db_error,
                     "tables": None if db_error else table_count()},
        "auth": {"linked": settings.AUTH_LINKED, **settings.project["auth"]},
        "endpoints": {"count": len(REGISTRY.endpoints),
                      "auto": sum(1 for e in REGISTRY.endpoints if e.source == "auto"),
                      "custom": sum(1 for e in REGISTRY.endpoints if e.source == "custom"),
                      "disabled": len(REGISTRY.disabled),
                      "list": [endpoint_dict(e) for e in REGISTRY.endpoints + REGISTRY.disabled]},
        "tests": {"custom": len(suite.tests)},
        # The JS API: where it is generated, or why it is not (it needs the molds of the template)
        "jsApi": {"dir": settings.JS_API_DIR, "notGenerated": generator.js_api_state()},
        "errors": {"config": settings.errors + scripts_missing(), "endpoints": REGISTRY.errors, "tests": suite.errors},
    })


###############################################################################
# Database
###############################################################################

def connection_args(v):
    try:
        return db_conn_of(v)
    except (TypeError, ValueError):
        raise HTTPError(400, f"The port must be a number, not {v.get('port')!r}")


@manage.route("/database/test", methods=["POST"])
def database_test():
    '''Tries a connection without saving it; if the user can connect, also the databases it sees'''
    a = connection_args(body())
    try:
        conn = get_conn(a, with_database=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW DATABASES")
                names = [r[0] for r in cur.fetchall()
                         if r[0] not in ("information_schema", "mysql", "performance_schema", "sys")]
        finally:
            conn.close()
    except pymysql.MySQLError as exc:
        return jsonify({"ok": False, "error": error_message(exc), "databases": []})
    error = test_connection(a) if a["database"] else None
    if error is None and a["database"] and a["database"] not in names:
        error = f"There is no database '{a['database']}' (or this user cannot see it)"
    return jsonify({"ok": error is None, "error": error, "databases": names})


@manage.route("/database/reload", methods=["POST"])
def database_reload():
    '''Creates the database again with the scripts of database.scripts, in order, as silence createdb
    of Silence 2 (e.g., to run the tests again from the original data)'''
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
    write_generated_tests()  # From the original data, which the tests will find
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
    rel = users_table.users_relation()
    if rel is None or rel.single_pk is None:
        raise HTTPError(409, "The users table does not exist or has no single primary key")
    return rel


@manage.route("/users")
def list_users():
    '''The users, with the state of their password (never its value)'''
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
        state = password_status(stored)
        return {"id": r[rel.single_pk], "identifier": get_field(r, users_table.identifier_field()),
                "role": get_field(r, a["role"]) if a["role"] else None,
                "active": get_field(r, a["active_status"]) if a["active_status"] else None,
                "password": state,
                # Stored as plain text (in plain mode, for practice databases): shown, to try the login
                "plainPassword": stored if settings.PASSWORD_MODE == "plain" and state == "plain" else None}
    users = [user(r) for r in rows]
    return jsonify({"pk": rel.single_pk, "passwordMode": settings.PASSWORD_MODE, "users": users})


@manage.route("/users/<user_id>/password", methods=["PUT"])
def set_password(user_id):
    '''Sets the password of a user (encrypted or not, as the project says)'''
    rel = users_rel()
    password = body().get("password")
    if not password:
        raise HTTPError(400, "The password cannot be empty")
    if not dal.query(f"SELECT 1 FROM `{rel.name}` WHERE `{rel.single_pk}` = %s", (user_id,)):
        raise HTTPError(404, "No such user")
    col = rel.column(settings.USER_AUTH_DATA["password"]).name
    dal.update(f"UPDATE `{rel.name}` SET `{col}` = %s WHERE `{rel.single_pk}` = %s", (hash_password(password), user_id))
    return jsonify({"updated": 1})


@manage.route("/users/<user_id>/session", methods=["POST"])
def user_session(user_id):
    '''Opens a session for a user without its password'''
    rel = users_rel()
    try:
        rows = dal.query(f"{users_table.users_select()} WHERE u.`{rel.single_pk}` = %s", (user_id,))
    except users_table.UsersTableError as exc:
        raise HTTPError(409, f"The users table is not well linked: {exc}")
    except DatabaseError as exc:
        raise to_http_error(exc)
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
    require_db()
    try:
        res = generator.generate(body().get("tables") or None)
    except ValueError as exc:
        raise HTTPError(400, str(exc))
    return jsonify(res)


@manage.route("/tests/generated")
def generated_tests():
    '''The generated tests: those of tests/auto_<table>.json, which Silence writes again whenever the
    endpoints change and when the database is created again (the custom ones are the files
    tests/<table>.json)'''
    require_db()
    if not test_model.load_generated():
        write_generated_tests()  # The first time (e.g., a project of a previous version)
    res = []
    for t in test_model.load_generated():
        d = t.to_dict()
        d["file"] = d["file"].removesuffix(".json")
        res.append(d)
    return jsonify({"tests": res})


###############################################################################
# The files of the project: silence.json, endpoints/*.json, tests/*.json and
# the log of requests (admin/logs/requests.log); and, only to read them, the
# generated JS API (js_api.dir) and its molds (.silence/js_api/). Each one is checked as what it
# is before saving it; the rest of the project is not reachable.
###############################################################################

NAME = r"[A-Za-z0-9_-]+"
READ_ONLY = ("log", "js", "mold", "sql")  # Written by Silence (the log, the JS API), the template (the molds) or the student (sql/)
TEXT = ("log", "js", "mold", "sql")       # Not JSON


def files():
    '''(pattern, kind, folder that is listed) of the files that can be managed'''
    res = [
        (re.compile(r"silence\.json"), "config", None),
        (re.compile(rf"endpoints/{NAME}\.json"), "endpoints", "endpoints"),
        (re.compile(rf"tests/{NAME}\.json"), "tests", "tests"),
        (re.compile(r"admin/logs/requests\.log"), "log", "admin/logs"),
        (re.compile(rf"sql/{NAME}\.sql"), "sql", "sql"),
        (re.compile(rf"{re.escape(molds.PROJECT_MOLDS)}/js_api/{NAME}\.js"), "mold", f"{molds.PROJECT_MOLDS}/js_api"),
    ]
    js_dir = settings.JS_API_DIR.strip("/")
    if js_dir:
        res.append((re.compile(rf"{re.escape(js_dir)}/{NAME}\.js"), "js", js_dir))
    return res


def file_kind(path):
    for pattern, kind, _ in files():
        if pattern.fullmatch(path):
            return kind
    raise HTTPError(403, f"'{path}' is not a file that can be managed: silence.json, endpoints/*.json, "
                         "tests/*.json, admin/logs/requests.log, or (only to read them) sql/*.sql, the JS API and its molds")


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
        clash = next((e for e in REGISTRY.endpoints + REGISTRY.disabled if e.key == ep.key and e.source == "custom"
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
    if not db_ok():
        raise HTTPError(409, "Without the database, the names of the generated tests (which a custom test "
                             "cannot take) cannot be checked: connect to it first")
    generated = test_model.generated_names() & set(entries)
    if generated:
        raise HTTPError(409, f"'{sorted(generated)[0]}' is the name of a generated test: choose another one")
    clash = next((t for t in test_model.load_tests().tests if t.name in entries and t.file != file), None)
    if clash:
        raise HTTPError(409, f"There is already a test '{clash.name}' in {clash.file}")


def save_config(data):
    '''silence.json: checked, and its connection tried, before saving it; the secret key is kept'''
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
        error = test_connection(db_conn_of({**old["database"], **db}))
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
    folders = [f for _, _, f in files() if f]
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
                if any(p.fullmatch(rel) for p, _, _ in files()) and os.path.isfile(os.path.join(where, name)):
                    res.append({"path": rel, "etag": etag_of(os.path.join(where, name))})
    return jsonify({"files": res})


@manage.route("/files/<path:path>")
def get_file(path):
    '''A file: its content (JSON, or the text of the log) and its version; null if it does not exist'''
    kind = file_kind(path)
    text, etag = read_with_etag(full_path(path))  # The content and its version, of the same reading
    if text is None or kind in TEXT:
        data = text
    else:
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise HTTPError(409, f"{path} is not valid JSON: {exc}")
        if kind == "config":  # With the default values of what is missing, and never the secret key
            data = {k: v for k, v in merge(DEFAULT_PROJECT, data).items() if k != "secret_key"} \
                if isinstance(data, dict) else data
    return jsonify({"path": path, "data": data, "etag": etag})


@manage.route("/files/<path:path>", methods=["PUT"])
def put_file(path):
    '''Saves a file (all of it), after checking it as what it is'''
    kind = file_kind(path)
    where = full_path(path)
    if kind in READ_ONLY:
        raise HTTPError(403, "The log is written by Silence: it can only be read or deleted" if kind == "log"
                        else f"{path} is only read here: the JS API is generated from its molds, which come "
                             "with the template")
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
        write_json(where, data)
        if kind == "endpoints":
            REGISTRY.load()
            write_generated_tests()
            generator.write_js_api_all()
    return jsonify({"path": path, "etag": etag_of(where), **extra}), 201 if created else 200


@manage.route("/files/<path:path>", methods=["DELETE"])
def delete_file(path):
    '''Deletes a file (the log: resets the activity and the statistics of the panel)'''
    kind = file_kind(path)
    where = full_path(path)
    if kind == "config":
        raise HTTPError(403, "silence.json cannot be deleted")
    if kind in ("js", "mold", "sql"):
        raise HTTPError(403, f"{path} is only read here")
    if kind in ("endpoints", "tests") and is_auto(path):
        raise HTTPError(403, f"{path} is autogenerated: generate the endpoints again instead")
    check_if_match(where)
    if not os.path.isfile(where):
        raise HTTPError(404, f"There is no {path}")
    os.remove(where)
    if kind == "endpoints":
        REGISTRY.load()
        write_generated_tests()
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
            created = op_id == "put_file"
            op = {"summary": summary, "operationId": op_id,
                  "responses": {"200": ok, **({"201": ok} if created else {}),
                                **({"400": {"description": "A script failed", **json_of(schemas.ref("ScriptError"))}}
                                   if op_id == "database_reload" else {}),
                                "default": {"description": "Error", **json_of(schemas.ref("Error"))}}}
            if op_id == "root":
                params = params + [{"name": "updates", "in": "query", "required": False, "schema": {"type": "string"},
                                    "description": "true: also the latest published versions (it goes to the network)"}]
            if op_id == "list_files":
                params = params + [{"name": "dir", "in": "query", "required": False, "schema": {"type": "string"},
                                    "description": "Only the files of this folder: endpoints, tests, admin/logs, sql, the JS API or its molds"}]
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
