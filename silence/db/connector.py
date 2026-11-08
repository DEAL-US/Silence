import pymysql
from pymysql.constants import CLIENT

from silence.db.errors import db_error_info
from silence.settings import settings

###############################################################################
# The connector builds the connections to the database.
###############################################################################


def get_conn(db_conn=None, with_database=True, autocommit=False):
    '''Opens a new connection with the project's settings (or the given ones, as DB_CONN). Without
    the database: to list the databases, or to drop and create it'''
    c = db_conn or settings.DB_CONN
    return pymysql.connect(
        host=c["host"],
        port=int(c["port"]),
        user=c["username"],
        password=c["password"],
        database=(c["database"] or None) if with_database else None,
        charset="utf8mb4",
        autocommit=autocommit,
        # rowcount of UPDATE is the number of matched rows, not of changed ones,
        # so that a PUT with the same values is not mistaken for a missing row
        client_flag=CLIENT.FOUND_ROWS,
        connect_timeout=5,
    )


def error_message(exc):
    '''The message of a PyMySQL exception'''
    return db_error_info(exc)[1]


def test_connection(db_conn):
    '''Tries to connect with the given parameters. Returns None if it works,
    or the error message otherwise'''
    try:
        get_conn(db_conn).close()
        return None
    except pymysql.MySQLError as exc:
        return error_message(exc)


def connection_error():
    '''Why Silence cannot use the project's database (None if it can)'''
    if not settings.DB_CONN["database"]:
        return "no database selected"
    return test_connection(settings.DB_CONN)
