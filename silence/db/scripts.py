import os

import pymysql

from silence.settings import settings

###############################################################################
# Creates the database again with the SQL scripts of the project's sql/ folder
# listed in silence.json (database.scripts), in that order, as 'silence
# createdb' of Silence 2 did with SQL_SCRIPTS: drops and creates the database,
# and runs each script after a USE. The scripts may change the delimiter
# (DELIMITER //), as the ones of the procedures and triggers do. From the admin
# panel (Reload), e.g., to run the tests again from the original data.
###############################################################################

SQL_DIR = "sql"


def sql_dir():
    return os.path.join(settings.PROJECT_DIR, SQL_DIR)


def split(text):
    '''The statements of a script: by its delimiter (";" or the one of DELIMITER), outside
    strings and comments. Returns [(line, statement)], line: where the statement starts'''
    statements = []
    delimiter = ";"
    current = []
    start = None
    quote = None        # The quote of the string we are in
    block = False       # Inside /* ... */
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if quote is None and not block and not "".join(current).strip() and stripped.upper().startswith("DELIMITER "):
            delimiter = stripped.split(None, 1)[1].strip()
            current, start = [], None
            continue
        i = 0
        buf = ""
        while i < len(line):
            c = line[i]
            if block:
                if line.startswith("*/", i):
                    block = False
                    i += 2
                    continue
                i += 1
                continue
            if quote:
                buf += c
                if c == "\\":
                    buf += line[i + 1:i + 2]
                    i += 2
                    continue
                if c == quote:
                    quote = None
                i += 1
                continue
            if line.startswith("--", i) or c == "#":
                break  # The rest of the line is a comment
            if line.startswith("/*", i):
                block = True
                i += 2
                continue
            if c in "'\"`":
                quote = c
                buf += c
                i += 1
                continue
            if line.startswith(delimiter, i):
                piece = ("\n".join(current + [buf])).strip()
                if piece:
                    statements.append((start or number, piece))
                current, buf, start = [], "", None
                i += len(delimiter)
                continue
            if start is None and not c.isspace():
                start = number
            buf += c
            i += 1
        current.append(buf)
    rest = "\n".join(current).strip()
    if rest:
        statements.append((start or 1, rest))
    return statements


class ScriptError(Exception):
    def __init__(self, file, line, statement, message):
        super().__init__(f"{file}, line {line}: {message}" if file and line else
                         f"{file}: {message}" if file else message)
        self.file, self.line, self.statement, self.message = file, line, statement, message


def reload():
    '''Drops and creates the database, and runs the scripts of database.scripts in order.
    Returns [{"file", "statements"}]; ScriptError (with the file, the line and the statement)
    at the first one that fails'''
    names = settings.project["database"].get("scripts") or []
    c = settings.DB_CONN
    db_name = c["database"]
    for name in names:  # All of them exist before dropping anything
        if not os.path.isfile(os.path.join(sql_dir(), name)):
            raise ScriptError(name, 0, "", f"there is no {SQL_DIR}/{name}")
    conn = pymysql.connect(host=c["host"], port=int(c["port"]), user=c["username"], password=c["password"],
                           charset="utf8mb4", autocommit=True, connect_timeout=5)
    done = []
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
                cur.execute(f"CREATE DATABASE `{db_name}`")
            except pymysql.MySQLError as exc:
                msg = exc.args[1] if len(exc.args) > 1 else str(exc)
                raise ScriptError("", 0, f"DROP/CREATE DATABASE `{db_name}`", msg)
            for name in names:
                cur.execute(f"USE `{db_name}`")
                with open(os.path.join(sql_dir(), name), encoding="utf8") as f:
                    statements = split(f.read())
                for line, statement in statements:
                    try:
                        cur.execute(statement)
                        while cur.nextset():
                            pass
                    except pymysql.MySQLError as exc:
                        msg = exc.args[1] if len(exc.args) > 1 else str(exc)
                        error = ScriptError(name, line, statement, msg)
                        error.done = done  # The scripts that did run
                        raise error
                done.append({"file": name, "statements": len(statements)})
    finally:
        conn.close()
    return done
