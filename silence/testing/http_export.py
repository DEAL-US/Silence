import json
import os
import re

from silence.db import dal
from silence.db.schema import get_schema
from silence.settings import settings
from silence.testing.model import load_tests, tests_dir

###############################################################################
# Export of the tests to .http files for VS Code's REST Client extension, to
# explore the API by hand (silence createtests --http). Unlike silence test,
# the requests are really sent: they change the database, and the checks of
# "expect" are only comments.
###############################################################################

HTTP_DIR = "http"
RE_VAR = re.compile(r"\$\{(\w+)\}")


def user_identifier(user_ref):
    '''The identifier (e.g., email) of a user given by its primary key'''
    auth = settings.USER_AUTH_DATA
    rel = get_schema().get(auth["table"]) if settings.AUTH_LINKED else None
    if rel is None or rel.single_pk is None:
        return str(user_ref)
    rows = dal.query(f"SELECT {auth['identifier']} AS i FROM {rel.name} WHERE {rel.single_pk} = %s", (user_ref,))
    return rows[0]["i"] if rows else str(user_ref)


def http_value(text, request_names):
    '''${var} of the tests becomes a reference to the response of a named request'''
    return RE_VAR.sub(lambda m: request_names.get(m.group(1), m.group(0)), text)


def export_table(table, tests, base_url):
    users = sorted({s["request"]["as"] for t in tests for s in t.steps if s["request"].get("as") is not None}, key=str)
    lines = [
        f"# Tests of {table}, exported by Silence for VS Code's REST Client extension.",
        "# Sending these requests CHANGES THE DATABASE (silence test rolls them back; this does not).",
        "# The checks of each test are in the comments (# Expect: ...).",
        "",
        f"@base = {base_url}",
    ]
    for u in users:
        lines.append(f"@password_{u} = ")
    lines.append("")

    pwd = settings.USER_AUTH_DATA["password"]
    id_col = settings.USER_AUTH_DATA["identifier"]
    for u in users:
        lines += [
            "###",
            f"# Login of user {u} (write its password above)",
            f"# @name login_{u}",
            "POST {{base}}/login",
            "Content-Type: application/json",
            "",
            json.dumps({id_col: user_identifier(u), pwd: f"{{{{password_{u}}}}}"}, ensure_ascii=False),
            "",
        ]

    for t in tests:
        names = {}
        for i, step in enumerate(t.steps):
            req = step["request"]
            name = f"{t.name}_{i + 1}"
            lines.append("###")
            if i == 0:
                lines.append(f"# {t.name}: {t.description}")
            expect = step.get("expect") or {}
            if expect:
                lines.append("# Expect: " + json.dumps(expect, ensure_ascii=False))
            lines.append(f"# @name {name}")
            method = req.get("method", "GET").upper()
            lines.append(f"{method} {{{{base}}}}{http_value(req['path'], names)}")
            if req.get("as") is not None:
                lines.append(f"Token: {{{{login_{req['as']}.response.body.$.sessionToken}}}}")
            if method in ("POST", "PUT") and req.get("body") is not None:
                body = http_value(json.dumps(req["body"], ensure_ascii=False, indent=2), names)
                lines += ["Content-Type: application/json", "", body]
            lines.append("")
            for var, where in (step.get("save") or {}).items():
                # JSONPath of REST Client: lastId -> $.lastId, 0.photo_id -> $[0].photo_id
                path = "$" + "".join(f"[{p}]" if p.isdigit() else f".{p}" for p in str(where).split("."))
                names[var] = f"{{{{{name}.response.body.{path}}}}}"
    return "\n".join(lines)


def export(tables=None):
    '''Writes tests/http/<table>.http and returns the written files'''
    suite = load_tests()
    by_table = {}
    for t in suite.tests:
        if tables is None or t.table in tables:
            by_table.setdefault(t.table, []).append(t)
    folder = os.path.join(tests_dir(), HTTP_DIR)
    os.makedirs(folder, exist_ok=True)
    base = f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}{settings.API_PREFIX}"
    written = []
    for table, tests in sorted(by_table.items()):
        path = os.path.join(folder, f"{table}.http")
        with open(path, "w", encoding="utf8") as f:
            f.write(export_table(table, tests, base))
        written.append(os.path.relpath(path, settings.PROJECT_DIR))
    return {"files": written}
