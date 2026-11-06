# Tests of the admin API of Silence 3 (/_silence/v1, docs/admin-api.md): the contract
# used by the admin panel. They leave the project as it was.
import requests
from silence.logging.default_logger import logger

from utils import BASE_URL

ADMIN = BASE_URL.replace("/api", "/_silence/v1")


def try_root_and_status():
    r = requests.get(ADMIN + "/")
    assert r.status_code == 200 and r.json()["api"] == 1
    s = requests.get(ADMIN + "/status").json()
    assert s["database"]["error"] is None
    assert s["auth"]["linked"] is True
    assert s["errors"] == {"endpoints": [], "tests": []}
    assert isinstance(s["revision"], int)


def try_config_without_secret():
    c = requests.get(ADMIN + "/config").json()
    assert "secret_key" not in c["config"] and c["etag"]
    r = requests.patch(ADMIN + "/config/database", json={"name": "does_not_exist_db"})
    assert r.status_code == 400  # Tested before saving: nothing changes
    r = requests.patch(ADMIN + "/config/nothing", json={})
    assert r.status_code == 404


def try_schema_and_users():
    names = [r["name"] for r in requests.get(ADMIN + "/schema").json()["relations"]]
    assert {"departments", "employees", "topemployees"} <= set(names)
    users = requests.get(ADMIN + "/users").json()["users"]
    assert users and all(u["password"] == "argon2" for u in users[:5])
    token = requests.post(f"{ADMIN}/users/{users[0]['id']}/session").json()["sessionToken"]
    r = requests.get(BASE_URL + "/employees/logged", headers={"Token": token})
    assert r.status_code == 200 and r.json()[0]["employeeId"] == users[0]["id"]
    assert requests.post(ADMIN + "/hash", json={"password": "x"}).json()["hash"].startswith("$argon2")


def try_endpoint_files():
    res = requests.get(ADMIN + "/endpoints").json()
    files = res["files"]
    assert "auto_employees" in files and "employees" in files
    # A new custom endpoint, with the version of its file
    data = {"route": "/departments/cities", "method": "GET", "sql": "SELECT DISTINCT city FROM departments"}
    r = requests.put(ADMIN + "/endpoints/departments_extra/cities", json=data, headers={"If-Match": ""})
    assert r.status_code == 201
    assert requests.get(BASE_URL + "/departments/cities").status_code == 200
    # An old version of the file is rejected; the same route twice too
    r = requests.put(ADMIN + "/endpoints/departments_extra/cities", json=data, headers={"If-Match": "old"})
    assert r.status_code == 412
    r = requests.put(ADMIN + "/endpoints/departments_extra/again", json=data)
    assert r.status_code == 409
    r = requests.put(ADMIN + "/endpoints/auto_departments/x", json=data)
    assert r.status_code == 400
    r = requests.delete(ADMIN + "/endpoints/departments_extra/cities")
    assert r.status_code == 200
    assert requests.get(BASE_URL + "/departments/cities").status_code in (404, 405)


def try_tests():
    tests = requests.get(ADMIN + "/tests").json()["tests"]
    assert tests
    r = requests.post(ADMIN + "/tests/run", json={"names": ["employees_salary_by_boss"]}).json()
    assert len(r["results"]) == 1 and r["results"][0]["passed"]
    steps = [{"request": {"method": "GET", "path": "/departments"}, "expect": {"status": 200}}]
    assert requests.post(ADMIN + "/tests/try", json={"steps": steps}).json()["steps"][0]["passed"]


def try_openapi():
    spec = requests.get(ADMIN + "/openapi.json").json()
    assert spec["openapi"].startswith("3.") and "/endpoints/{file}/{name}" in spec["paths"]


def run():
    print("Testing the admin API...")
    for name, test in [("root and status", try_root_and_status), ("config", try_config_without_secret),
                       ("schema and users", try_schema_and_users), ("endpoint files", try_endpoint_files),
                       ("tests", try_tests), ("openapi", try_openapi)]:
        logger.warning("testing the admin API: %s", name)
        test()
