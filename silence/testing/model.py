import json
import os

from silence.settings import settings
from silence.exceptions import TestDefinitionError

###############################################################################
# Tests: unit tests (one request and what is expected). Silence does not run
# them: the admin panel does, against the student's API.
#
#   generated  computed by Silence from the endpoints and the data whenever they
#              are asked for (silence/testing/generator.py): they are not files,
#              so they always follow the endpoints, and they are not edited.
#   custom     tests/<table>.json, written by the student (from the admin panel),
#              e.g., for the business rules. Their names cannot be the names of
#              generated tests.
# The scenarios (sequences of unit tests) belong to the admin panel.
#
#   "employees_updateSalary_403": {
#       "description": "An employee who is not the boss cannot change a salary",
#       "endpoint": "PUT /employees/$employeeId/salary",
#       "PUT /employees/4/salary": {"salary": 9000},
#       "as": 1,
#       "expect": 403
#   }
#
#   "METHOD path": the request (path after the API prefix), and its value the
#       body (null without body).
#   as: the primary key of the user that sends the request (no password
#       needed); missing or null: no session.
#   expect: the status (403), or {"status": 400, "message": "validSalary"}
#       (a text contained in the error message). Without expect, or without
#       status, any 2xx status is expected.
#
# The long form also works: {"request": {"method", "path", "body", "as"}, "expect": {...}}.
###############################################################################

TESTS_DIR = "tests"
AUTO_PREFIX = "auto_"
METHODS = ("GET", "POST", "PUT", "DELETE")
EXPECT_KEYS = {"status", "message"}


def normalize_expect(expect, where):
    if expect is None:
        return {}
    if isinstance(expect, int) and not isinstance(expect, bool):
        return {"status": expect}
    if not isinstance(expect, dict) or set(expect) - EXPECT_KEYS:
        raise TestDefinitionError(f"{where}: expect must be a status (e.g., 403) or an object with "
                                  "status and message (a text of the error message)")
    return dict(expect)


def short_unit(test):
    '''A unit test given as {description, endpoint, request: {method, path, body, as}, expect},
    written in the short form'''
    req = test["request"]
    res = {k: test[k] for k in ("description", "endpoint") if test.get(k)}
    res[f"{req['method']} {req['path']}"] = req.get("body")
    if req.get("as") is not None:
        res["as"] = req["as"]
    expect = test.get("expect") or {}
    if set(expect) == {"status"}:
        res["expect"] = expect["status"]
    elif expect:
        res["expect"] = expect
    return res


def tests_dir():
    return os.path.join(settings.PROJECT_DIR, TESTS_DIR)


UNIT_KEYS = {"description", "endpoint", "as", "expect", "request"}


def parse_unit(data, where):
    '''The request of a unit test (short or long form), as {method, path, body, as}'''
    if "request" in data:  # Long form
        req = data["request"]
        if not isinstance(req, dict) or not isinstance(req.get("path"), str):
            raise TestDefinitionError(f"{where} has no request.path")
        request = {"method": str(req.get("method", "GET")).upper(), "path": req["path"],
                   "body": req.get("body"), "as": req.get("as", data.get("as"))}
        unknown = set(data) - UNIT_KEYS
    else:  # Short form: "METHOD path": body
        keys = [k for k in data if k not in UNIT_KEYS]
        if len(keys) != 1 or " " not in keys[0]:
            raise TestDefinitionError(f"{where} must have one request, as \"GET /photos\": null "
                                      "(a sequence of tests is a scenario, in the admin panel)")
        method, path = keys[0].split(" ", 1)
        request = {"method": method.upper(), "path": path.strip(), "body": data[keys[0]], "as": data.get("as")}
        unknown = set()
    if unknown:
        raise TestDefinitionError(f"{where}: unknown keys {', '.join(sorted(unknown))}")
    if request["method"] not in METHODS:
        raise TestDefinitionError(f"{where}: unknown method {request['method']}")
    if not request["path"].startswith("/"):
        raise TestDefinitionError(f"{where}: the path must start with / (after the API prefix)")
    return request


class Test:
    '''A unit test. filename: its file (for a generated one, the file where it would be saved
    if it is customized); source: "auto" (generated) or "custom"'''
    def __init__(self, name, data, filename, source="custom"):
        self.name = name
        self.file = os.path.basename(filename)
        self.table = os.path.splitext(self.file)[0]
        self.source = source
        if not isinstance(data, dict):
            raise TestDefinitionError(f"'{name}' in {self.file} must be an object")
        self.data = data
        self.description = data.get("description", "")
        self.endpoint = data.get("endpoint", "")
        where = f"'{name}' in {self.file}"
        if "steps" in data:
            raise TestDefinitionError(f"{where} has steps: the tests of tests/ are unit tests (one request); "
                                      "the scenarios (sequences of tests) belong to the admin panel")
        self.request = parse_unit(data, where)
        self.expect = normalize_expect(data.get("expect"), where)

    def to_dict(self):
        return {"name": self.name, "file": self.file, "table": self.table, "source": self.source,
                "description": self.description, "endpoint": self.endpoint, "definition": self.data,
                "request": {"method": self.request["method"], "path": self.request["path"],
                            "body": self.request["body"], "as": self.request["as"]},
                "expect": self.expect}


class Suite:
    def __init__(self, tests, errors):
        self.tests = tests
        self.errors = errors

    def get(self, name):
        return next((t for t in self.tests if t.name == name), None)


def load_tests():
    '''The custom tests (tests/<table>.json) and the errors of their files'''
    tests, errors = [], []
    folder = tests_dir()
    files = sorted(f for f in os.listdir(folder) if f.endswith(".json")) if os.path.isdir(folder) else []
    for filename in files:
        path = os.path.join(folder, filename)
        if filename.startswith(AUTO_PREFIX):
            errors.append(f"{filename}: the generated tests are not saved any more (Silence computes them): "
                          "delete this file (copy first the tests that you changed to tests/<table>.json)")
            continue
        if os.path.getsize(path) == 0:
            continue  # Just created by an editor: as if it did not exist yet
        try:
            with open(path, encoding="utf8") as f:
                content = json.load(f)
            if not isinstance(content, dict):
                raise TestDefinitionError(f"{filename} must contain an object with one entry per test")
        except (json.JSONDecodeError, TestDefinitionError) as exc:
            errors.append(f"{filename}: {exc}")
            continue
        for name, data in content.items():
            try:
                tests.append(Test(name, data, path))
            except (TestDefinitionError, AttributeError, TypeError) as exc:
                errors.append(str(exc))

    by_name = {}
    for t in tests:
        by_name.setdefault(t.name, []).append(t)
    duplicated = {n for n, ts in by_name.items() if len(ts) > 1}
    for n in sorted(duplicated):
        errors.append(f"the test '{n}' is in more than one file "
                      f"({', '.join(t.file for t in by_name[n])}): none of them is loaded")
    return Suite([t for t in tests if t.name not in duplicated], errors)


def generated_names():
    '''The names of the generated tests (empty if they cannot be generated)'''
    try:
        from silence.testing.generator import generated_tests
        return {t.name for t in generated_tests()}
    except Exception:
        return set()


def all_tests():
    '''The generated tests (if the database is reachable) and the custom ones. A custom test with
    the name of a generated one is not loaded (an error says so)'''
    suite = load_tests()
    generated = []
    try:
        from silence.testing.generator import generated_tests
        generated = generated_tests()
    except Exception as exc:  # E.g., the database is not reachable: only the custom ones
        suite.errors.append(f"the tests cannot be generated: {exc}")
    names = {t.name for t in generated}
    for t in suite.tests:
        if t.name in names:
            suite.errors.append(f"'{t.name}' in {t.file} has the name of a generated test: rename it")
    customs = [t for t in suite.tests if t.name not in names]
    return Suite(generated + customs, suite.errors)
