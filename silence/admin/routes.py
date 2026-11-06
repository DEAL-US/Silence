import json
import os

from flask import Blueprint, jsonify, request, send_from_directory, redirect

from silence import __version__
from silence.auth.passwords import password_status, hash_password
from silence.db import dal, schema as db_schema
from silence.db.connector import test_connection
from silence.db.errors import to_http_error
from silence.exceptions import HTTPError, DatabaseError
from silence.settings import settings
from silence.server import stats
from silence.server.endpoints import REGISTRY, endpoints_dir, AUTO_PREFIX, route_key, Endpoint
from silence.server.session import get_field
from silence.testing import model as test_model

###############################################################################
# The admin panel (/admin): a static single-page app (admin/static) and its
# JSON API (/admin/api/...). Only reachable from the same computer.
###############################################################################

STATIC = os.path.join(os.path.dirname(__file__), "static")
admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.before_request
def only_local():
    if request.remote_addr not in ("127.0.0.1", "::1", None):
        raise HTTPError(403, "The admin panel can only be used from this computer")


def body():
    return request.get_json(silent=True) or {}


def db_ok():
    return bool(settings.DB_CONN["database"]) and test_connection(settings.DB_CONN) is None


###############################################################################
# Static files
###############################################################################

@admin.route("/")
def index():
    return send_from_directory(STATIC, "index.html", max_age=0)


@admin.route("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        raise HTTPError(404, f"Unknown admin API {path}")
    return send_from_directory(STATIC, path, max_age=0)


###############################################################################
# Status and settings
###############################################################################

@admin.route("/api/status")
def status():
    db_error = test_connection(settings.DB_CONN) if settings.DB_CONN["database"] else "no database selected"
    suite = test_model.load_tests()
    return jsonify({
        "version": __version__,
        "project": os.path.basename(settings.PROJECT_DIR),
        "projectDir": settings.PROJECT_DIR,
        "apiPrefix": settings.API_PREFIX,
        "baseUrl": f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}",
        "database": {"name": settings.DB_CONN["database"], "error": db_error},
        "auth": {"linked": settings.AUTH_LINKED, **settings.project["auth"]},
        "endpoints": {"count": len(REGISTRY.endpoints),
                      "auto": sum(1 for e in REGISTRY.endpoints if e.source == "auto"),
                      "custom": sum(1 for e in REGISTRY.endpoints if e.source == "custom"),
                      "errors": REGISTRY.errors},
        "tests": {"count": len(suite.tests), "errors": suite.errors},
    })


@admin.route("/api/config")
def get_config():
    return jsonify({k: v for k, v in settings.project.items() if k != "secret_key"})


@admin.route("/api/config/<section>", methods=["PUT"])
def put_config(section):
    values = body()
    if section == "database":
        new = {**settings.project["database"], **values}
        error = test_connection({"host": new["host"], "port": new["port"], "username": new["user"],
                                 "password": new["password"], "database": new["name"]})
        if error:
            raise HTTPError(400, f"Cannot connect: {error}")
    if section not in ("database", "auth", "server", "debug"):
        raise HTTPError(400, f"Unknown section {section}")
    settings.update(section, values)
    db_schema.invalidate()
    if section in ("database", "auth"):
        REGISTRY.load()
    return jsonify({"saved": True, "restartNeeded": section == "server"})


@admin.route("/api/db/test", methods=["POST"])
def db_test():
    v = body()
    error = test_connection({"host": v.get("host"), "port": v.get("port", 3306), "username": v.get("user"),
                             "password": v.get("password"), "database": v.get("name") or None})
    return jsonify({"ok": error is None, "error": error})


@admin.route("/api/db/databases", methods=["POST"])
def db_databases():
    '''The databases that the given user can see (to choose one in the setup)'''
    import pymysql
    v = body()
    try:
        conn = pymysql.connect(host=v.get("host"), port=int(v.get("port", 3306)), user=v.get("user"),
                               password=v.get("password"), connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES")
            names = [r[0] for r in cur.fetchall()
                     if r[0] not in ("information_schema", "mysql", "performance_schema", "sys")]
        conn.close()
        return jsonify({"ok": True, "databases": names})
    except pymysql.MySQLError as exc:
        return jsonify({"ok": False, "error": exc.args[1] if len(exc.args) > 1 else str(exc)})


@admin.route("/api/schema")
def get_schema():
    if not db_ok():
        raise HTTPError(409, "The database is not configured")
    return jsonify(db_schema.get_schema(refresh=True).to_dict())


###############################################################################
# Users
###############################################################################

def users_rel():
    if not settings.AUTH_LINKED:
        raise HTTPError(409, "The users table is not linked")
    rel = db_schema.get_schema().get(settings.USER_AUTH_DATA["table"])
    if rel is None or rel.single_pk is None:
        raise HTTPError(409, "The users table does not exist or has no single primary key")
    return rel


@admin.route("/api/users")
def list_users():
    rel = users_rel()
    a = settings.USER_AUTH_DATA
    try:
        rows = dal.query(f"SELECT * FROM {rel.name} ORDER BY {rel.single_pk} LIMIT 500")
    except DatabaseError as exc:
        raise to_http_error(exc)
    res = []
    for r in rows:
        res.append({"id": r[rel.single_pk], "identifier": get_field(r, a["identifier"]),
                    "role": get_field(r, a["role"]) if a["role"] else None,
                    "active": get_field(r, a["active_status"]) if a["active_status"] else None,
                    "password": password_status(get_field(r, a["password"]))})
    return jsonify({"pk": rel.single_pk, "users": res, "passwordMode": settings.PASSWORD_MODE})


@admin.route("/api/users/<user_id>/password", methods=["PUT"])
def set_password(user_id):
    rel = users_rel()
    password = body().get("password")
    if not password:
        raise HTTPError(400, "The password cannot be empty")
    col = rel.column(settings.USER_AUTH_DATA["password"]).name
    try:
        res = dal.update(f"UPDATE {rel.name} SET {col} = %s WHERE {rel.single_pk} = %s",
                         (hash_password(password), user_id))
    except DatabaseError as exc:
        raise to_http_error(exc)
    if res["affectedRows"] == 0:
        raise HTTPError(404, "No such user")
    return jsonify({"saved": True})


@admin.route("/api/users/passwords", methods=["PUT"])
def set_all_passwords():
    '''Sets the same password for every user (handy with the sample data)'''
    rel = users_rel()
    password = body().get("password")
    if not password:
        raise HTTPError(400, "The password cannot be empty")
    col = rel.column(settings.USER_AUTH_DATA["password"]).name
    ids = [r[rel.single_pk] for r in dal.query(f"SELECT {rel.single_pk} FROM {rel.name}")]
    for uid in ids:
        dal.update(f"UPDATE {rel.name} SET {col} = %s WHERE {rel.single_pk} = %s", (hash_password(password), uid))
    return jsonify({"saved": len(ids)})


@admin.route("/api/users/<user_id>/token", methods=["POST"])
def user_token(user_id):
    '''Opens a session for a user without its password, to try the endpoints'''
    from silence.server.auth_endpoints import session_for
    rel = users_rel()
    rows = dal.query(f"SELECT * FROM {rel.name} WHERE {rel.single_pk} = %s", (user_id,))
    if not rows:
        raise HTTPError(404, "No such user")
    return jsonify(session_for(rows[0]))


###############################################################################
# Endpoints
###############################################################################

def read_file(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf8") as f:
        return json.load(f)


def write_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not data:
        if os.path.isfile(path):
            os.remove(path)
        return
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


@admin.route("/api/endpoints")
def list_endpoints():
    REGISTRY.load()
    return jsonify({"endpoints": [e.to_dict() for e in REGISTRY.endpoints], "errors": REGISTRY.errors,
                    "apiPrefix": settings.API_PREFIX})


@admin.route("/api/endpoints/generate", methods=["POST"])
def generate_endpoints():
    from silence.server import generator
    if not db_ok():
        raise HTTPError(409, "The database is not configured")
    tables = body().get("tables") or None
    return jsonify(generator.generate(tables))


@admin.route("/api/endpoints/customize", methods=["POST"])
def customize_endpoint():
    '''Moves an autogenerated endpoint to the custom file of its table'''
    v = body()
    ep = REGISTRY.find(v.get("method", ""), v.get("route", ""))
    if ep is None or ep.source != "auto":
        raise HTTPError(404, "There is no such autogenerated endpoint")
    auto_path = os.path.join(endpoints_dir(), ep.file)
    custom_path = os.path.join(endpoints_dir(), f"{ep.table}.json")
    auto, custom = read_file(auto_path), read_file(custom_path)
    data = auto.pop(ep.name)
    name = ep.name if ep.name not in custom else f"{ep.name}_custom"
    custom[name] = data
    write_file(custom_path, custom)
    write_file(auto_path, auto)
    REGISTRY.load()
    return jsonify({"file": os.path.basename(custom_path), "name": name})


@admin.route("/api/endpoints/custom", methods=["PUT"])
def save_custom_endpoint():
    '''Creates or replaces a custom endpoint: {file, name, oldName?, data}'''
    v = body()
    file = os.path.basename(v.get("file") or "")
    name, data = v.get("name"), v.get("data")
    if not file.endswith(".json") or file.startswith(AUTO_PREFIX):
        raise HTTPError(400, "Custom endpoints go in endpoints/<table>.json")
    if not name or not isinstance(data, dict):
        raise HTTPError(400, "An endpoint needs a name and its data")
    path = os.path.join(endpoints_dir(), file)
    try:
        Endpoint(name, data, path)  # Validates it
    except Exception as exc:
        raise HTTPError(400, str(exc))

    key = route_key(data.get("method", "GET"), data.get("route", ""))
    clash = next((e for e in REGISTRY.endpoints if e.key == key
                  and not (e.file == file and e.name in (name, v.get("oldName")))), None)
    if clash:
        raise HTTPError(409, f"{key} is already defined as '{clash.name}' in {clash.file}")

    content = read_file(path)
    if v.get("oldName") and v["oldName"] != name:
        content.pop(v["oldName"], None)
    content[name] = data
    write_file(path, content)
    REGISTRY.load()
    return jsonify({"saved": True})


@admin.route("/api/endpoints/custom", methods=["DELETE"])
def delete_custom_endpoint():
    v = body()
    file = os.path.basename(v.get("file") or "")
    if file.startswith(AUTO_PREFIX):
        raise HTTPError(400, "Autogenerated endpoints are removed by generating them again")
    path = os.path.join(endpoints_dir(), file)
    content = read_file(path)
    if content.pop(v.get("name"), None) is None:
        raise HTTPError(404, "No such endpoint")
    write_file(path, content)
    REGISTRY.load()
    return jsonify({"deleted": True})


###############################################################################
# Tests
###############################################################################

@admin.route("/api/tests")
def list_tests():
    suite = test_model.load_tests()
    return jsonify({"tests": [t.to_dict() for t in suite.tests], "errors": suite.errors})


@admin.route("/api/tests/generate", methods=["POST"])
def generate_tests():
    from silence.testing import generator
    if not db_ok():
        raise HTTPError(409, "The database is not configured")
    return jsonify(generator.generate(body().get("tables") or None))


@admin.route("/api/tests/run", methods=["POST"])
def run_tests():
    from silence.testing import runner
    if not db_ok():
        raise HTTPError(409, "The database is not configured")
    suite = test_model.load_tests()
    return jsonify({"results": runner.run_tests(suite, body().get("names") or None), "errors": suite.errors})


@admin.route("/api/tests/try", methods=["POST"])
def try_steps():
    '''Runs some steps in test mode (rolled back), e.g., while composing a test'''
    from silence.testing import runner
    steps = body().get("steps")
    if not isinstance(steps, list) or not steps:
        raise HTTPError(400, "No steps")
    return jsonify({"steps": runner.truncate(runner.run_test_steps(steps))})


@admin.route("/api/tests/custom", methods=["PUT"])
def save_custom_test():
    '''Creates or replaces a custom test: {file, name, oldName?, data}'''
    v = body()
    file = os.path.basename(v.get("file") or "")
    name, data = v.get("name"), v.get("data")
    if not file.endswith(".json") or file.startswith(test_model.AUTO_PREFIX):
        raise HTTPError(400, "Custom tests go in tests/<table>.json")
    path = os.path.join(test_model.tests_dir(), file)
    try:
        test_model.Test(name, data, path)
    except Exception as exc:
        raise HTTPError(400, str(exc))
    suite = test_model.load_tests()
    clash = next((t for t in suite.tests if t.name == name and t.file != file), None)
    if clash:
        raise HTTPError(409, f"There is already a test '{name}' in {clash.file}")
    content = read_file(path)
    if v.get("oldName") and v["oldName"] != name:
        content.pop(v["oldName"], None)
    content[name] = data
    write_file(path, content)
    return jsonify({"saved": True})


@admin.route("/api/tests/customize", methods=["POST"])
def customize_test():
    '''Moves an autogenerated test to the custom file of its table'''
    name = body().get("name")
    t = test_model.load_tests().get(name)
    if t is None or t.source != "auto":
        raise HTTPError(404, "There is no such autogenerated test")
    auto_path = os.path.join(test_model.tests_dir(), t.file)
    custom_path = os.path.join(test_model.tests_dir(), f"{t.table}.json")
    auto, custom = read_file(auto_path), read_file(custom_path)
    custom[name] = auto.pop(name)
    write_file(custom_path, custom)
    write_file(auto_path, auto)
    return jsonify({"file": os.path.basename(custom_path)})


@admin.route("/api/tests/custom", methods=["DELETE"])
def delete_custom_test():
    v = body()
    file = os.path.basename(v.get("file") or "")
    if file.startswith(test_model.AUTO_PREFIX):
        raise HTTPError(400, "Autogenerated tests are removed by generating them again")
    path = os.path.join(test_model.tests_dir(), file)
    content = read_file(path)
    if content.pop(v.get("name"), None) is None:
        raise HTTPError(404, "No such test")
    write_file(path, content)
    return jsonify({"deleted": True})


###############################################################################
# Statistics
###############################################################################

@admin.route("/api/stats")
def get_stats():
    return jsonify(stats.snapshot())


@admin.route("/api/stats", methods=["DELETE"])
def reset_stats():
    stats.reset()
    return jsonify({"reset": True})
