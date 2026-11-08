import json

from silence.db import dal
from silence.db.schema import get_schema
from silence.settings import settings
from silence.server.endpoints import REGISTRY
from silence.server.session import get_field
from silence.auth.users import is_users_table, users_pk
from silence.testing.model import Test, short_unit

###############################################################################
# Generation of tests from the endpoints, computed whenever they are asked for
# (they are not saved). For each endpoint, with the status expected:
#   positive: the request that should work (2xx);
#   negative: no session (401), another role (403), another owner (403),
#             a row that does not exist (404), a required param missing (400).
# Silence does not run them: the admin panel does. They are not edited; the
# custom tests (tests/<table>.json) cannot use their names.
###############################################################################

TEST_PASSWORD = "Test-1234"
MISSING_INT = 999999999


class Context:
    '''Data of the database used to build the requests'''
    def __init__(self):
        self.schema = get_schema(refresh=True)
        self.rows = {}
        self.users = []
        self.auth = settings.USER_AUTH_DATA
        if settings.AUTH_LINKED:
            self.users = self.sample(self.auth["table"], limit=200)

    def sample(self, table, limit=50):
        if table not in self.rows:
            rel = self.schema.get(table)
            if rel is None:
                self.rows[table] = []
            else:
                order = f" ORDER BY {rel.single_pk}" if rel.single_pk else ""
                self.rows[table] = dal.query(f"SELECT * FROM {rel.name}{order} LIMIT {int(limit)}")
        return self.rows[table]

    def user_ref(self, user):
        return get_field(user, users_pk()) if user else None

    def role(self, user):
        return get_field(user, self.auth["role"]) if self.auth["role"] else None

    def allowed_user(self, roles, owner_id=None):
        '''A user that can call the endpoint (and owns the row, if given)'''
        for u in self.users:
            if owner_id is not None and str(self.user_ref(u)) != str(owner_id):
                continue
            if "*" in roles or self.role(u) in roles:
                return u
        return None

    def other_role_user(self, roles):
        if "*" in roles or not self.auth["role"]:
            return None
        return next((u for u in self.users if self.role(u) not in roles), None)

    def other_user(self, roles, owner_id):
        return next((u for u in self.users if str(self.user_ref(u)) != str(owner_id)
                     and ("*" in roles or self.role(u) in roles)), None)

    def referenced(self, table, row):
        '''Whether other rows reference this one (then it cannot be deleted)'''
        for ref_table, fk in self.schema.referencing(table):
            value = row.get(fk["refColumn"])
            if value is not None and dal.query(
                    f"SELECT 1 FROM {ref_table.name} WHERE {fk['column']} = %s LIMIT 1", (value,)):
                return True
        return False


def unit(method, path, as_user=None, body=None, expect=None):
    '''A unit test (long form, written later in the short form)'''
    req = {"method": method, "path": path}
    if as_user is not None:
        req["as"] = as_user
    if body is not None:
        req["body"] = body
    return {"request": req, "expect": expect or {}}


def fill_route(route, values):
    path = route
    for p, v in values.items():
        path = path.replace("$" + p, str(v))
    return path


def route_values(ep, rel, row):
    '''Values for the $params of the route, taken from a row (None if one is unknown)'''
    values = {}
    for p in ep.url_params:
        col = rel.column(p) if rel else None
        if col is None or row is None or row.get(col.name) is None:
            return None
        values[p] = row[col.name]
    return values


def missing_values(ep, rel):
    values = {}
    for p in ep.url_params:
        col = rel.column(p) if rel else None
        numeric = col is not None and col.data_type in ("int", "bigint", "smallint", "tinyint", "mediumint", "decimal")
        values[p] = MISSING_INT if numeric else "missing-value"
    return values


def variants(value, n):
    '''Variants of a value that keep its format (so as not to break a CHECK on it, e.g., the
    format of a DNI): the last group of digits changed (00001A → 00002A, 00003A...), or, without
    digits, a prefix in the local part of an email (t1.druiz@us.es) or a suffix (-t1)'''
    import re
    text = str(value)
    digits = list(re.finditer(r"\d+", text))
    if digits:
        m = digits[-1]
        width = len(m.group())
        for i in range(1, 1000):
            number = str(int(m.group()) + n * i).zfill(width)[-width:]
            yield text[:m.start()] + number + text[m.end():]
    if "@" in text:
        for i in range(n, n + 50):
            yield f"t{i}.{text}"
    for i in range(n, n + 50):
        yield f"{text}-t{i}"


def unique_value(col, value, n, rel=None):
    '''A variant of a value of a UNIQUE column that does not collide (checked in the table)'''
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value + 100000 + n
    for candidate in variants(value, n):
        if col.max_length and len(candidate) > col.max_length:
            continue
        if rel is None or not dal.query(f"SELECT 1 FROM {rel.name} WHERE {col.name} = %s LIMIT 1", (candidate,)):
            return candidate
    return f"{value}-t{n}"[-(col.max_length or 0):]


def free_reference(rel, col):
    '''For a primary key that is also a foreign key (a subclass of an inheritance, with the id of
    its superclass): a value of the referenced table that the table does not use yet, or None'''
    fk = next((f for f in rel.fks if f["column"] == col.name), None)
    if fk is None:
        return None
    rows = dal.query(f"SELECT r.{fk['refColumn']} AS v FROM {fk['refTable']} r WHERE r.{fk['refColumn']} "
                     f"NOT IN (SELECT {col.name} FROM {rel.name} WHERE {col.name} IS NOT NULL) "
                     f"ORDER BY r.{fk['refColumn']} LIMIT 1")
    return rows[0]["v"] if rows else None


def json_value(value):
    '''A DB value as it travels in a JSON body'''
    return json.loads(json.dumps(value, default=lambda o: str(o) if not hasattr(o, "isoformat")
                                 else o.isoformat().replace("T", " ")))


def body_from_row(ep, rel, row, ctx, mutate_uniques, n=1):
    body = {}
    uniques = rel.unique_columns() if rel else set()
    pwd = ctx.auth["password"].lower() if settings.AUTH_LINKED else None
    is_users = rel is not None and is_users_table(rel.name)
    for p in ep.body_params:
        col = rel.column(p) if rel else None
        if ep.owner and col is not None and col.name.lower() == ep.owner.lower():
            continue
        if is_users and col is not None and col.name.lower() == pwd:
            body[p] = TEST_PASSWORD
            continue
        value = row.get(col.name) if (col is not None and row) else None
        if value is not None and mutate_uniques and col.name in uniques:
            if col.name in rel.pk and any(f["column"] == col.name for f in rel.fks):
                value = free_reference(rel, col)  # The id of a superclass row that is not one of these yet
                if value is None:
                    return None  # Every row of the superclass is already one: no positive POST
            else:
                value = unique_value(col, value, n, rel)
        body[p] = json_value(value)
    if mutate_uniques and rel is not None:
        free_combinations(rel, body)
    return body


def free_combinations(rel, body):
    '''For the UNIQUE indexes of several columns (e.g., the pair of FKs of an
    N:M table), looks for a combination of referenced values that is not used'''
    params = {(rel.column(p).name if rel.column(p) else p): p for p in body}
    fk_of = {fk["column"]: fk for fk in rel.fks}
    for cols in rel.uniques:
        if len(cols) < 2 or not all(c in params for c in cols):
            continue
        where = " AND ".join(f"{c} = %s" for c in cols)
        taken = lambda values: dal.query(f"SELECT 1 FROM {rel.name} WHERE {where} LIMIT 1", values)
        current = [body[params[c]] for c in cols]
        if not taken(current):
            continue
        # Candidates: the values of the referenced rows for FK columns
        candidates = []
        for c in cols:
            fk = fk_of.get(c)
            if fk:
                refs = dal.query(f"SELECT DISTINCT {fk['refColumn']} AS v FROM {fk['refTable']} LIMIT 30")
                candidates.append([r["v"] for r in refs])
            else:
                value = body[params[c]]
                options = [value]
                if value is not None:
                    options.append(json_value(unique_value(rel.column(c), value, 1)))
                candidates.append(options)
        found = None
        def search(i, chosen):
            nonlocal found
            if found is not None:
                return
            if i == len(cols):
                # Two FKs to the same table with the same value (e.g., following
                # oneself) are usually forbidden by a CHECK: avoid them
                refs = [(fk_of[c]["refTable"], v) for c, v in zip(cols, chosen) if c in fk_of]
                if len(set(refs)) < len(refs):
                    return
                if not taken(chosen):
                    found = list(chosen)
                return
            for v in candidates[i]:
                search(i + 1, chosen + [v])
                if found is not None:
                    return
        search(0, [])
        if found is not None:
            for c, v in zip(cols, found):
                body[params[c]] = json_value(v)


def required_param(ep, rel):
    '''A body param whose column is required (to test that it is missing)'''
    for p in ep.body_params:
        col = rel.column(p) if rel else None
        if col is not None and not col.optional and not (ep.owner and col.name.lower() == ep.owner.lower()):
            return p
    return None


def tests_for_endpoint(ep, ctx):
    rel = ctx.schema.get(ep.shape.table) if ep.shape is not None else ctx.schema.get(ep.table)
    rows = ctx.sample(rel.name) if rel else []
    needs_user = ep.auth_required or bool(ep.owner)
    base = f"{ep.table}_{ep.name}"
    label = f"{ep.method} {ep.route}"
    tests = {}

    def add(case, description, test):
        tests[f"{base}_{case}"] = {"description": f"{label}: {description}", "endpoint": label, **test}

    # The row used by the positive case, and its user
    row, user = None, None
    if ep.method in ("PUT", "DELETE"):
        for r in rows:
            if ep.method == "DELETE" and ctx.referenced(rel.name, r):
                continue
            owner_id = r.get(ep.owner) if ep.owner else None
            if ep.owner and owner_id is None:
                continue  # A row without owner cannot be changed by anybody
            u = ctx.allowed_user(ep.allowed_roles, owner_id) if needs_user else None
            if needs_user and u is None:
                continue
            row, user = r, u
            break
    else:
        row = rows[0] if rows else None
        if needs_user:
            user = ctx.allowed_user(ep.allowed_roles)
    positive_row = row
    if row is None and ep.method in ("PUT", "DELETE"):
        # No row for the positive case: the negative ones can use any row
        row = rows[0] if rows else None
        if needs_user:
            owner_id = row.get(ep.owner) if (ep.owner and row) else None
            user = ctx.allowed_user(ep.allowed_roles, owner_id) or ctx.allowed_user(ep.allowed_roles)
    as_user = ctx.user_ref(user)
    can_run = not needs_user or user is not None

    # The params of the route: from the row (None if one is unknown), or values that do not exist
    values = route_values(ep, rel, row) if ep.url_params else {}
    path = fill_route(ep.route, values) if values is not None else None
    missing_path = fill_route(ep.route, missing_values(ep, rel)) if rel else None

    # Positive case (not with params of the query string: their values cannot be guessed)
    if can_run and path is not None and not ep.query_params:
        if ep.method == "GET":
            add("ok", "returns the current rows", unit("GET", path, as_user, expect={"status": 200}))
        elif ep.method == "POST" and row is not None:
            body = body_from_row(ep, rel, row, ctx, mutate_uniques=True)
            if body is not None:
                add("ok", "creates a row", unit("POST", path, as_user, body, {"status": 201}))
        elif ep.method == "PUT" and positive_row is not None:
            body = body_from_row(ep, rel, row, ctx, mutate_uniques=False)
            add("ok", "updates a row (with its current values)", unit("PUT", path, as_user, body, {"status": 200}))
        elif ep.method == "DELETE" and positive_row is not None:
            add("ok", "deletes a row that no other row references", unit("DELETE", path, as_user, expect={"status": 200}))

    # A row that does not exist
    if ep.url_params and ep.method in ("GET", "PUT", "DELETE") and can_run and rel is not None and not ep.query_params:
        body = body_from_row(ep, rel, row, ctx, False) if ep.method == "PUT" and row else None
        add("not_found", "a row that does not exist is a 404", unit(ep.method, missing_path, as_user, body, {"status": 404}))

    # A required param missing
    if ep.method == "POST" and can_run and row is not None and path is not None:
        p = required_param(ep, rel)
        if p:
            body = body_from_row(ep, rel, row, ctx, mutate_uniques=True) or body_from_row(ep, rel, row, ctx, False)
            body.pop(p, None)
            add("missing_param", f"without '{p}' is a 400", unit("POST", path, as_user, body, {"status": 400, "message": p}))

    # A param of the query string missing
    if ep.query_params and can_run and path is not None:
        p = ep.query_params[0]
        add("missing_query", f"without '{p}' in the query string is a 400",
            unit(ep.method, path, as_user, None, {"status": 400, "message": p}))

    # Sessions, roles and owners
    any_path = path or missing_path
    if needs_user and any_path is not None:
        body = (body_from_row(ep, rel, row, ctx, True) or body_from_row(ep, rel, row, ctx, False)) \
            if ep.method in ("POST", "PUT") and row else None
        add("no_session", "without a session is a 401", unit(ep.method, any_path, None, body, {"status": 401}))

        other = ctx.other_role_user(ep.allowed_roles)
        if other is not None:
            add("wrong_role", f"with the role {ctx.role(other)!r} is a 403",
                unit(ep.method, any_path, ctx.user_ref(other), body, {"status": 403}))

        if ep.owner and ep.method in ("PUT", "DELETE") and row is not None and path is not None:
            intruder = ctx.other_user(ep.allowed_roles, row.get(ep.owner))
            if intruder is not None:
                add("not_owner", "by a user who is not the owner is a 403",
                    unit(ep.method, path, ctx.user_ref(intruder), body, {"status": 403}))

    return tests


def generated_tests():
    '''The tests of all the endpoints, computed now from the endpoints and the data (they are not
    saved): a list of Test, each one with the file of its table (where it goes if it is customized)'''
    REGISTRY.load()
    ctx = Context()
    tests = []
    for ep in sorted(REGISTRY.endpoints, key=lambda e: (e.table, e.route, e.method)):
        for name, t in tests_for_endpoint(ep, ctx).items():
            # The short form, the same as the custom tests (and so the example for them)
            tests.append(Test(name, short_unit(t), f"{ep.table}.json", source="auto"))
    return tests
