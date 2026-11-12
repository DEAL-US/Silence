"""Runs the unit tests of a running Silence project (the generated ones and the custom ones of
tests/*.json, read with the file API) through HTTP, as the admin panel does:
Silence does not run tests. Used by the CI (run_ci.py); not part of Silence.

The requests are real: they change the database. They run in the order GET, POST, PUT, DELETE
(as the admin panel does), so that the reads see the original data and the deletions go last.

Usage: python run_units.py http://127.0.0.1:8080   (exit code 0 only if all pass)
"""
import sys

import requests

from silence.testing.model import Test

ORDER = {"GET": 0, "POST": 1, "PUT": 2, "DELETE": 3}


def check(expect, status, data):
    '''The failures of a response against what a test expects (without status, a 2xx)'''
    failures = []
    if "status" in expect:
        if expect["status"] != status:
            failures.append(f"expected status {expect['status']}, got {status}")
    elif not 200 <= status < 300:
        failures.append(f"expected a 2xx status, got {status}")
    if "message" in expect:
        msg = data.get("message", "") if isinstance(data, dict) else ""
        if expect["message"] not in (msg or ""):
            failures.append(f"expected a message with {expect['message']!r}, got {msg!r}")
    return failures


def main(base):
    admin = base + "/_silence/v1"
    info = requests.get(admin + "/").json()
    api = base + info["studentApi"]["prefix"]
    header = info["studentApi"]["sessionHeader"]
    tests = requests.get(admin + "/tests/generated").json()["tests"]
    errors = requests.get(admin + "/status").json()["errors"]["tests"]
    for err in errors:
        print("Test error:", err)
    for f in requests.get(admin + "/files", params={"dir": "tests"}).json()["files"]:
        if f["path"].startswith("tests/auto_"):
            continue  # The generated ones, already in /tests/generated
        content = requests.get(f"{admin}/files/{f['path']}").json()["data"]
        for name, definition in content.items():
            tests.append(Test(name, definition, f["path"]).to_dict())
    tests.sort(key=lambda t: ORDER.get(t["request"]["method"], 9))
    passed = 0
    for t in tests:
        req = t["request"]
        headers = {}
        if req.get("as") is not None:
            headers[header] = requests.post(f"{admin}/users/{req['as']}/session").json()["sessionToken"]
        body = req.get("body") if req["method"] in ("POST", "PUT") else None
        resp = requests.request(req["method"], api + req["path"], json=body, headers=headers)
        try:
            data = resp.json()
        except ValueError:
            data = None
        failures = check(t["expect"], resp.status_code, data)
        if failures:
            print(f"FAIL  {t['name']} ({t['file']}): {req['method']} {req['path']} -> {'; '.join(failures)}")
        else:
            passed += 1
    print(f"{passed} of {len(tests)} tests passed")
    return 0 if passed == len(tests) and not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8080"))
