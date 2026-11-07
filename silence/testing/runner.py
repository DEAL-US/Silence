import json
import re

from silence.db import dal
from silence.db.connector import rollback_transaction
from silence.db.schema import get_schema
from silence.settings import settings

###############################################################################
# Runs tests through the API (Flask's test client, in the same process), each
# test inside a transaction that is rolled back: the database is left as it
# was. The requests of the tests are neither logged nor counted in the stats.
###############################################################################

TEST_HEADER = "X-Silence-Test"
RE_VAR = re.compile(r"\$\{(\w+)\}")


def substitute(value, variables):
    '''Replaces ${name} with the saved variables (keeping the type if the whole value is one)'''
    if isinstance(value, str):
        m = re.fullmatch(r"\$\{(\w+)\}", value)
        if m and m.group(1) in variables:
            return variables[m.group(1)]
        return RE_VAR.sub(lambda m: str(variables.get(m.group(1), m.group(0))), value)
    if isinstance(value, dict):
        return {k: substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, variables) for v in value]
    return value


def extract(data, path):
    '''Value of "lastId", "0.photo_id", "user.email"... in the response'''
    for part in str(path).split("."):
        if isinstance(data, list):
            try:
                data = data[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(data, dict):
            data = data.get(part)
        else:
            return None
    return data


def token_for(user_ref):
    '''Session token of a user of the linked users table, by primary key (or identifier)'''
    from silence.server.auth_endpoints import session_for
    if user_ref is None or not settings.AUTH_LINKED:
        return None
    auth = settings.USER_AUTH_DATA
    rel = get_schema().get(auth["table"])
    rows = []
    if rel and rel.single_pk:
        rows = dal.query(f"SELECT * FROM {rel.name} WHERE {rel.single_pk} = %s", (user_ref,))
    if not rows:
        rows = dal.query(f"SELECT * FROM {auth['table']} WHERE {auth['identifier']} = %s", (user_ref,))
    if not rows:
        raise LookupError(f"there is no user {user_ref!r} in {auth['table']}")
    return session_for(rows[0])["sessionToken"]


def same(expected, actual):
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return float(expected) == float(actual)
    return expected == actual


def check(expect, status, data):
    failures = []
    if "status" in expect:
        if expect["status"] != status:
            failures.append(f"expected status {expect['status']}, got {status}")
    elif not 200 <= status < 300:
        failures.append(f"expected a 2xx status, got {status}")
    if "count" in expect:
        n = len(data) if isinstance(data, list) else None
        if n != expect["count"]:
            failures.append(f"expected {expect['count']} rows, got {n}")
    if "row" in expect:
        row = data[0] if isinstance(data, list) and data else data
        if not isinstance(row, dict):
            failures.append("expected a row, got none")
        else:
            for k, v in expect["row"].items():
                if not same(v, row.get(k)):
                    failures.append(f"expected {k} = {v!r}, got {row.get(k)!r}")
    if "message" in expect:
        msg = data.get("message", "") if isinstance(data, dict) else ""
        if expect["message"] not in (msg or ""):
            failures.append(f"expected a message with {expect['message']!r}, got {msg!r}")
    return failures


def run_steps(steps, client):
    '''Runs the steps of a test. Returns the result of each step (it stops at the first failure)'''
    variables, results = {}, []
    for i, step in enumerate(steps):
        req = substitute(step.get("request", {}), variables)
        method = req.get("method", "GET").upper()
        path = req["path"]
        res = {"index": i, "method": method, "path": path, "passed": False, "failures": []}
        try:
            headers = {TEST_HEADER: "1"}
            token = token_for(req.get("as"))
            if token:
                headers["Token"] = token
            resp = client.open(settings.API_PREFIX + path, method=method, headers=headers,
                               json=req.get("body") if method in ("POST", "PUT") else None)
            data = resp.get_json(silent=True)
            res["status"] = resp.status_code
            res["response"] = data
            res["failures"] = check(step.get("expect", {}), resp.status_code, data)
            for var, where in (step.get("save") or {}).items():
                variables[var] = extract(data, where)
        except Exception as exc:
            res["failures"] = [f"{type(exc).__name__}: {exc}"]
        res["passed"] = not res["failures"]
        results.append(res)
        if not res["passed"]:
            break
    return results


def run_test_steps(steps):
    '''Runs some steps (short or long form) in test mode (rolled back) and returns their results.
    TestDefinitionError if a step is not valid'''
    from silence.server.manager import APP
    from silence.testing.model import normalize_step
    steps = [normalize_step(step, i) for i, step in enumerate(steps)]
    with rollback_transaction():
        return run_steps(steps, APP.test_client())


def run_tests(suite, names=None):
    results = []
    for test in suite.tests:
        if names and test.name not in names:
            continue
        steps = run_test_steps(test.steps)
        passed = all(s["passed"] for s in steps) and len(steps) == len(test.steps)
        results.append({"name": test.name, "file": test.file, "source": test.source,
                        "table": test.table, "passed": passed, "steps": truncate(steps)})
    return results


def truncate(steps, max_chars=2000):
    '''Keeps the responses short in the results'''
    for s in steps:
        text = json.dumps(s.get("response"), default=str, ensure_ascii=False)
        if len(text) > max_chars:
            s["response"] = text[:max_chars] + "…"
    return steps
