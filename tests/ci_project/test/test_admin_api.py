# Tests of the admin API of Silence 3 (/_silence/v1, docs/admin-api.md): the contract
# used by the admin panel. They leave the project as it was.
import requests
from silence.logging.default_logger import logger

from utils import BASE_URL

ADMIN = BASE_URL.replace("/api", "/_silence/v1")
FILES = ADMIN + "/files/"


def read(path):
    return requests.get(FILES + path).json()


def write(path, data, etag=None):
    headers = {"If-Match": etag} if etag is not None else {}
    return requests.put(FILES + path, json=data, headers=headers)


def try_root_and_status():
    r = requests.get(ADMIN + "/")
    assert r.status_code == 200 and r.json()["api"] == 1
    s = requests.get(ADMIN + "/status").json()
    assert s["database"]["error"] is None
    assert s["auth"]["linked"] is True
    assert s["errors"] == {"config": [], "endpoints": [], "tests": []}
    assert isinstance(s["revision"], int)
    # The endpoints that are being served, with their files
    names = {(e["file"], e["name"]) for e in s["endpoints"]["list"]}
    assert ("employees", "updateSalary") in names and len(names) == s["endpoints"]["count"]


def try_config_file():
    c = read("silence.json")
    config, etag = c["data"], c["etag"]
    assert "secret_key" not in config and etag
    # Tested before saving: nothing changes
    r = write("silence.json", {**config, "database": {**config["database"], "name": "does_not_exist_db"}})
    assert r.status_code == 400 and "connect" in r.json()["message"]
    # Invalid values and unknown keys are not saved
    r = write("silence.json", {**config, "auth": {**config["auth"], "password_mode": "whatever"}})
    assert r.status_code == 400 and "password_mode" in r.json()["message"]
    assert write("silence.json", {**config, "server": {**config["server"], "port": "eight"}}).status_code == 400
    assert write("silence.json", {**config, "nothing": 1}).status_code == 400
    assert write("silence.json", [1]).status_code == 400
    assert read("silence.json")["etag"] == etag
    # Saved (the secret key is kept: the sessions still work), with the version that was read
    r = write("silence.json", {**config, "debug": True}, etag)
    assert r.status_code == 200 and r.json()["restartNeeded"] is False
    assert write("silence.json", config, etag).status_code == 412
    assert write("silence.json", config, r.json()["etag"]).status_code == 200
    assert read("silence.json")["data"] == config
    assert requests.get(ADMIN + "/status").json()["errors"]["config"] == []
    assert requests.delete(FILES + "silence.json").status_code == 403


def try_other_files():
    # Only the files of the project that Silence manages
    for path in ("sql/create_tables.sql", "../x.json", "endpoints/%2E%2E/silence.json", "web/index.html",
                 "endpoints/a.b.json", "admin/js/main.js"):
        assert requests.get(FILES + path).status_code in (403, 404), path
    listing = requests.get(ADMIN + "/files").json()["files"]
    paths = [f["path"] for f in listing]
    assert "silence.json" in paths and "endpoints/auto_employees.json" in paths and "tests/employees.json" in paths
    assert all(f["path"].startswith("tests/") for f in requests.get(ADMIN + "/files?dir=tests").json()["files"])
    assert requests.get(ADMIN + "/files?dir=sql").status_code == 400
    # Nothing else of the project (e.g., the panel's own files)
    assert requests.get(FILES + "admin/data/x.json").status_code == 403
    assert write("admin/data/x.json", []).status_code == 403


def try_schema_and_users():
    relations = {r["name"]: r for r in requests.get(ADMIN + "/schema").json()["relations"]}
    assert {"departments", "employees", "topemployees"} <= set(relations)
    assert relations["departments"]["rows"] > 0
    users = requests.get(ADMIN + "/users").json()["users"]
    assert users and all(u["password"] == "argon2" and u["plainPassword"] is None for u in users[:5])
    token = requests.post(f"{ADMIN}/users/{users[0]['id']}/session").json()["sessionToken"]
    r = requests.get(BASE_URL + "/employees/logged", headers={"Token": token})
    assert r.status_code == 200 and r.json()[0]["employeeId"] == users[0]["id"]


def endpoint(name):
    return next((e for e in requests.get(ADMIN + "/status").json()["endpoints"]["list"] if e["name"] == name), None)


def try_endpoint_files():
    path = "endpoints/departments_extra.json"
    cities = {"route": "/departments/cities", "method": "GET", "sql": "SELECT DISTINCT city FROM departments"}
    r = write(path, {"cities": cities}, "")
    assert r.status_code == 201
    assert requests.get(BASE_URL + "/departments/cities").status_code == 200
    # An old version of the file is rejected; the same route twice too; a wrong endpoint too
    assert write(path, {"cities": cities}, "old").status_code == 412
    assert write(path, {"cities": cities, "again": cities}).status_code == 409
    assert write(path, {"cities": {**cities, "method": "FETCH"}}).status_code == 400
    assert write(path, {"bad name": cities}).status_code == 400
    # The autogenerated files are only read: they are written by generating them
    assert read("endpoints/auto_departments.json")["data"]
    assert write("endpoints/auto_departments.json", {}).status_code == 403
    assert requests.delete(FILES + "endpoints/auto_departments.json").status_code == 403
    # A custom endpoint prevails over the autogenerated one with the same method and route
    over = {"route": "/departments/$departmentId", "method": "GET",
            "sql": "SELECT name FROM departments WHERE departmentId = $departmentId"}
    assert write(path, {"cities": cities, "getOne": over}).status_code == 200
    assert list(requests.get(BASE_URL + "/departments/1").json()[0]) == ["name"]
    assert endpoint("getOne")["overrides"] == ["auto_departments.json"]
    assert requests.get(ADMIN + "/status").json()["errors"]["endpoints"] == []
    # The params of the query string that the SQL uses (filters of a collection)
    above = {"route": "/departments/above", "method": "GET", "query_params": ["minId"],
             "sql": "SELECT * FROM departments WHERE departmentId > $minId"}
    assert write(path, {"cities": cities, "above": above}).status_code == 200
    assert len(requests.get(BASE_URL + "/departments/1").json()[0]) > 1
    rows = requests.get(BASE_URL + "/departments/above?minId=1").json()
    assert rows and all(r["departmentId"] > 1 for r in rows)
    r = requests.get(BASE_URL + "/departments/above")
    assert r.status_code == 400 and "minId" in r.json()["message"]
    assert requests.delete(FILES + path).status_code == 200
    assert requests.get(BASE_URL + "/departments/cities").status_code in (404, 405)
    assert endpoint("above") is None


def try_tests():
    generated = requests.get(ADMIN + "/tests/generated").json()["tests"]
    # The generated tests are computed (not saved), each one with the file of its table and a status
    assert generated and all(t["source"] == "auto" and t["expect"].get("status")
                             and not t["file"].startswith("auto_") for t in generated)
    # Silence does not run tests nor generates, customizes or exports files of tests
    for path in ("/tests", "/tests/run", "/tests/generate", "/tests/export"):
        assert requests.post(ADMIN + path, json={}).status_code in (404, 405), path
    # The generated tests are not edited: a custom test cannot take the name of one
    mine = {"description": "mine", "GET /departments/999999999": None, "expect": 404}
    assert write("tests/ci_check.json", {"departments_getById_not_found": mine}).status_code == 409
    assert write("tests/ci_check.json", {"departments_mine": mine}).status_code == 201
    # Nor the name of a custom test of another file
    assert write("tests/ci_check2.json", {"departments_mine": mine}).status_code == 409
    # A test has one request, and expects a status and a message
    assert write("tests/ci_check.json", {"flow": {"steps": ["a"]}}).status_code == 400
    assert write("tests/ci_check.json", {"rows": {"GET /departments": None, "expect": {"count": 3}}}).status_code == 400
    assert requests.delete(FILES + "tests/ci_check.json").status_code == 200


def log_lines():
    data = read("admin/logs/requests.log")["data"]
    return data.splitlines() if data else []


def try_request_log():
    """The requests to the student's app, one line each, in admin/logs/requests.log"""
    requests.delete(FILES + "admin/logs/requests.log")
    requests.get(BASE_URL + "/departments/1?x=a%20b")
    requests.get(BASE_URL + "/nothing")
    requests.post(BASE_URL + "/login", json={"email": "nobody@company.com", "password": "x"})
    requests.get(ADMIN + "/status")  # The admin API (the panel) is not logged
    lines = log_lines()
    assert len(lines) == 3, lines
    fields = [line.split(" ", 8) for line in lines]
    assert fields[0][1:5] == ["api", "GET", "/api/departments/1?x=a%20b", "200"]
    assert fields[0][5].endswith("ms") and fields[0][6].endswith("B") and fields[0][7] == "/departments/$departmentId"
    assert fields[1][1] == "api" and fields[1][4] == "404" and fields[1][7] == "-" and "nothing" in fields[1][8]
    assert fields[2][1:4] == ["silence", "POST", "/api/login"] and fields[2][7] == "/login"
    assert write("admin/logs/requests.log", "x").status_code == 403
    assert requests.delete(FILES + "admin/logs/requests.log").status_code == 200
    requests.get(BASE_URL + "/departments")
    assert len(log_lines()) == 1  # Created again


def try_openapi():
    spec = requests.get(ADMIN + "/openapi.json").json()
    assert spec["openapi"].startswith("3.") and "/files/{path}" in spec["paths"]
    assert len([op for ops in spec["paths"].values() for op in ops]) == 14  # And openapi.json


def try_response_schemas():
    """Every response follows its schema of the OpenAPI specification (the contract)"""
    from jsonschema import Draft202012Validator
    spec = requests.get(ADMIN + "/openapi.json").json()

    def check(op_id, response, status=None):
        if status is not None:
            assert response.status_code == status, (op_id, response.status_code, response.text[:200])
        op = next(o for ops in spec["paths"].values() for o in ops.values() if o["operationId"] == op_id)
        code = str(response.status_code)
        ref = (op["responses"].get(code) or op["responses"]["default"])["content"]["application/json"]["schema"]
        schema = {**ref, "components": spec["components"]}
        errors = list(Draft202012Validator(schema).iter_errors(response.json()))
        assert not errors, (op_id, [e.message for e in errors[:3]])

    config = requests.get(FILES + "silence.json")
    check("get_file", config, 200)
    config, etag = config.json()["data"], config.json()["etag"]
    db = config["database"]
    conn = {"host": db["host"], "port": db["port"], "user": db["user"], "password": db["password"]}
    check("root", requests.get(ADMIN + "/"), 200)
    check("status", requests.get(ADMIN + "/status"), 200)
    check("put_file", write("silence.json", config, etag), 200)
    check("put_file", write("silence.json", {**config, "debug": "x"}), 400)
    test = requests.post(ADMIN + "/database/test", json={**conn, "name": db["name"]})
    check("database_test", test, 200)
    assert test.json()["ok"] and db["name"] in test.json()["databases"]
    wrong = requests.post(ADMIN + "/database/test", json={**conn, "name": "does_not_exist_db"})
    check("database_test", wrong, 200)
    assert not wrong.json()["ok"] and wrong.json()["databases"]
    check("get_schema", requests.get(ADMIN + "/schema"), 200)
    users = requests.get(ADMIN + "/users")
    check("list_users", users, 200)
    uid = users.json()["users"][0]["id"]
    check("user_session", requests.post(f"{ADMIN}/users/{uid}/session"), 200)
    check("list_files", requests.get(ADMIN + "/files"), 200)
    check("get_file", requests.get(FILES + "endpoints/employees.json"), 200)
    check("get_file", requests.get(FILES + "nothing.json"), 403)
    data = {"names": {"route": "/departments/names", "method": "GET", "sql": "SELECT name FROM departments"}}
    check("put_file", write("endpoints/schema_check.json", data), 201)
    check("put_file", write("endpoints/schema_check.json", data), 200)
    check("put_file", write("endpoints/schema_check.json", data, "old"), 412)
    check("delete_file", requests.delete(FILES + "endpoints/schema_check.json"), 200)
    check("generated_tests", requests.get(ADMIN + "/tests/generated"), 200)
    # The scripts must exist in sql/ (nothing is saved otherwise)
    scripts = {**config, "database": {**db, "scripts": ["create_tables.sql", "nope.sql"]}}
    r = write("silence.json", scripts)
    assert r.status_code == 400 and "sql/nope.sql" in r.json()["message"]
    assert read("silence.json")["data"]["database"]["scripts"][-1] == "populate_database.sql"
    # The database created again with database.scripts, as silence createdb of Silence 2
    reloaded = requests.post(ADMIN + "/database/reload")
    check("database_reload", reloaded, 200)
    assert [s["file"] for s in reloaded.json()["scripts"]] == ["create_tables.sql", "create_views.sql",
                                                              "populate_database.sql"]
    assert requests.get(BASE_URL + "/departments").status_code == 200


def run():
    print("Testing the admin API...")
    for name, test in [("root and status", try_root_and_status), ("silence.json", try_config_file),
                       ("other files", try_other_files), ("schema and users", try_schema_and_users),
                       ("endpoint files", try_endpoint_files), ("tests", try_tests),
                       ("request log", try_request_log), ("openapi", try_openapi),
                       ("response schemas", try_response_schemas)]:
        logger.warning("testing the admin API: %s", name)
        test()
