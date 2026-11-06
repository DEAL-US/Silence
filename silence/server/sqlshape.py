import re

###############################################################################
# A minimal analysis of the shape of the simple SQL statements used by the
# endpoints, to apply the rules that depend on them (optional columns, owner,
# password hashing):
#
#   INSERT INTO t (c1, c2) VALUES (v1, v2)
#   UPDATE t SET c1 = v1, c2 = v2 [WHERE ...]
#   DELETE FROM t [WHERE ...]
#
# Statements with other shapes are run as they are, without those rules.
###############################################################################

RE_PARAM = re.compile(r"\$(\w+)")
RE_IDENT = r"`?(\w+)`?"
RE_INSERT = re.compile(r"^\s*INSERT\s+INTO\s+" + RE_IDENT + r"\s*\((.*?)\)\s*VALUES\s*\((.*)\)\s*;?\s*$", re.I | re.S)
RE_UPDATE = re.compile(r"^\s*UPDATE\s+" + RE_IDENT + r"\s+SET\s+(.*?)(?:\s+WHERE\s+(.*?))?\s*;?\s*$", re.I | re.S)
RE_DELETE = re.compile(r"^\s*DELETE\s+FROM\s+" + RE_IDENT + r"(?:\s+WHERE\s+(.*?))?\s*;?\s*$", re.I | re.S)
RE_ASSIGN = re.compile(r"^\s*" + RE_IDENT + r"\s*=\s*(.+?)\s*$", re.S)
RE_ONLY_PARAM = re.compile(r"^\s*\$(\w+)\s*$")


def sql_op(sql):
    '''The SQL operation of a statement, in uppercase (SELECT, INSERT, CALL...)'''
    m = re.match(r"\s*(\w+)", sql)
    op = m.group(1).upper() if m else ""
    return "SELECT" if op in ("WITH", "SHOW", "DESCRIBE", "EXPLAIN") else op


def params_of(text):
    '''Names of the $params in a route or a SQL statement, in order, without repetitions'''
    res = []
    for p in RE_PARAM.findall(text or ""):
        if p not in res:
            res.append(p)
    return res


def split_top_level(text, sep=","):
    '''Splits by sep, ignoring the separators inside parentheses and quotes'''
    parts, depth, quote, current = [], 0, None, ""
    for ch in text:
        if quote:
            current += ch
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def only_param(expr):
    '''The param name if the expression is exactly "$param", else None'''
    m = RE_ONLY_PARAM.match(expr)
    return m.group(1) if m else None


class Insert:
    def __init__(self, table, pairs):
        self.table = table
        self.pairs = pairs  # [(column, value expression)]

    def sql(self):
        cols = ", ".join(c for c, _ in self.pairs)
        vals = ", ".join(v for _, v in self.pairs)
        return f"INSERT INTO {self.table}({cols}) VALUES ({vals})"


class Update:
    def __init__(self, table, pairs, where):
        self.table = table
        self.pairs = pairs  # [(column, value expression)]
        self.where = where

    def sql(self):
        sets = ", ".join(f"{c} = {v}" for c, v in self.pairs)
        where = f" WHERE {self.where}" if self.where else ""
        return f"UPDATE {self.table} SET {sets}{where}"


class Delete:
    def __init__(self, table, where):
        self.table = table
        self.where = where


def parse(sql):
    '''Returns an Insert, Update or Delete if the statement has a simple shape, else None'''
    m = RE_INSERT.match(sql)
    if m:
        cols = [c.strip().strip("`") for c in split_top_level(m.group(2))]
        vals = split_top_level(m.group(3))
        if len(cols) == len(vals) and all(re.fullmatch(r"\w+", c) for c in cols):
            return Insert(m.group(1), list(zip(cols, vals)))
        return None

    m = RE_UPDATE.match(sql)
    if m:
        pairs = []
        for assignment in split_top_level(m.group(2)):
            a = RE_ASSIGN.match(assignment)
            if not a:
                return None
            pairs.append((a.group(1), a.group(2)))
        return Update(m.group(1), pairs, m.group(3))

    m = RE_DELETE.match(sql)
    if m:
        return Delete(m.group(1), m.group(2))

    return None


def to_pyformat(sql):
    '''Converts the $params of Silence into PyMySQL's %(param)s placeholders'''
    return RE_PARAM.sub(r"%(\1)s", sql.replace("%", "%%"))
