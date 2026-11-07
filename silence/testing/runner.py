import json

from silence.db import dal
from silence.db.connector import rollback_transaction
from silence.db.schema import get_schema
from silence.settings import settings

###############################################################################
# Runs tests through the API (Flask's test client, in the same process), each
# test inside a transaction that is rolled back: the database is left as it
# was. The requests of the tests count in the statistics, but they are not logged in the console.
###############################################################################

TEST_HEADER = "X-Silence-Test"


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


def run_test(test, client):
    '''Runs a unit test. Returns its result as a list of one step (the format of the results)'''
    req = test.request
    res = {"index": 0, "test": test.name, "method": req["method"], "path": req["path"],
           "passed": False, "failures": []}
    try:
        headers = {TEST_HEADER: "1"}
        token = token_for(req.get("as"))
        if token:
            headers["Token"] = token
        resp = client.open(settings.API_PREFIX + req["path"], method=req["method"], headers=headers,
                           json=req.get("body") if req["method"] in ("POST", "PUT") else None)
        data = resp.get_json(silent=True)
        res["status"] = resp.status_code
        res["response"] = data
        res["failures"] = check(test.expect, resp.status_code, data)
    except Exception as exc:
        res["failures"] = [f"{type(exc).__name__}: {exc}"]
    res["passed"] = not res["failures"]
    return [res]


def run_isolated(test):
    '''Runs a test in test mode: in a transaction that is rolled back'''
    from silence.server.manager import APP
    with rollback_transaction():
        return run_test(test, APP.test_client())


def try_definition(definition):
    '''Runs a test that is not saved (e.g., while editing it). TestDefinitionError if it is not valid'''
    from silence.testing.model import Test
    return truncate(run_isolated(Test("(not saved)", definition, "try.json")))


def run_tests(suite, names=None):
    results = []
    for test in suite.tests:
        if names and test.name not in names:
            continue
        steps = run_isolated(test)
        results.append({"name": test.name, "file": test.file, "source": test.source, "table": test.table,
                        "passed": steps[0]["passed"], "steps": truncate(steps)})
    return results


def truncate(steps, max_chars=2000):
    '''Keeps the responses short in the results'''
    for s in steps:
        text = json.dumps(s.get("response"), default=str, ensure_ascii=False)
        if len(text) > max_chars:
            s["response"] = text[:max_chars] + "…"
    return steps
