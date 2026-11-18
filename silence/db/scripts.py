import os
import re

import pymysql

from silence.db.connector import get_conn, error_message
from silence.settings import settings, PROJECT_FILE

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


def missing(names):
    '''The scripts of a list that are not in sql/'''
    return [n for n in names if not os.path.isfile(os.path.join(sql_dir(), n))]


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
    '''A script that failed: where, the statement, the message and the scripts that did run'''
    def __init__(self, file, line, statement, message, done=()):
        super().__init__(f"{file}, line {line}: {message}" if file and line else
                         f"{file}: {message}" if file else message)
        self.file, self.line, self.statement, self.message = file, line, statement, message
        self.done = list(done)


# The statements that name a database: CREATE/DROP DATABASE|SCHEMA [IF [NOT] EXISTS] x, and USE x
NAMES_DB = re.compile(r"^(?:(?:CREATE|DROP)\s+(?:DATABASE|SCHEMA)\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?|USE\s+)`?(\w+)`?",
                      re.IGNORECASE)


def databases_named(statements):
    '''The databases that some statements name (in order, once; ignoring case)'''
    found = {}
    for _, statement in statements:
        m = NAMES_DB.match(statement)
        if m:
            found.setdefault(m.group(1).lower(), m.group(1))
    return list(found.values())


def scripts_problem(named, db_name):
    '''Why some scripts cannot load the database of the project (None if they can): the database of a
    project is the one that its scripts create, so if they name one, it must be that one, and only one
    (DEAL-US/Silence#24). The scripts of the course name it themselves (DROP DATABASE IF EXISTS
    grades_db; CREATE DATABASE grades_db; USE grades_db;), because they are also run in HeidiSQL: with
    another one configured, they would drop and fill theirs, and leave the configured one empty'''
    if len(named) > 1:
        return f"The scripts name more than one database ({', '.join(named)}): they must create only one"
    if named and named[0].lower() != str(db_name).lower():
        return (f"The scripts create {named[0]}, and the project uses {db_name} ({PROJECT_FILE}): "
                "change the scripts or the database")
    return None


def reload():
    '''Drops and creates the database, and runs the scripts of database.scripts in order.
    Returns [{"file", "statements"}]; ScriptError (with the file, the line and the statement)
    at the first one that fails'''
    names = settings.project["database"].get("scripts") or []
    db_name = settings.DB_CONN["database"]
    absent = missing(names)  # All of them exist before dropping anything
    if absent:
        raise ScriptError(absent[0], 0, "", f"there is no {SQL_DIR}/{absent[0]}")
    # Read and checked before dropping anything
    scripts = {}
    for name in names:
        with open(os.path.join(sql_dir(), name), encoding="utf8") as f:
            scripts[name] = split(f.read())
    problem = scripts_problem(databases_named([s for st in scripts.values() for s in st]), db_name)
    if problem:
        raise ScriptError("", 0, "", problem)
    conn = get_conn(with_database=False, autocommit=True)
    done = []
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
                cur.execute(f"CREATE DATABASE `{db_name}`")
            except pymysql.MySQLError as exc:
                raise ScriptError("", 0, f"DROP/CREATE DATABASE `{db_name}`", error_message(exc))
            for name in names:
                cur.execute(f"USE `{db_name}`")
                statements = scripts[name]
                for line, statement in statements:
                    try:
                        cur.execute(statement)
                        while cur.nextset():
                            pass
                    except pymysql.MySQLError as exc:
                        raise ScriptError(name, line, statement, error_message(exc), done)
                done.append({"file": name, "statements": len(statements)})
    finally:
        conn.close()
    return done
