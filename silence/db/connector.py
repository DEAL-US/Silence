import threading

import pymysql
from pymysql.constants import CLIENT

from silence.db.errors import db_error_info
from silence.settings import settings

###############################################################################
# The connector builds the connections to the database.
###############################################################################


class _Connection(pymysql.connections.Connection):
    '''A PyMySQL connection that shares its TLS context with the others. Without TLS options, PyMySQL
    uses TLS if the server offers it (without checking certificates), and creates a new context for
    each connection, which loads all the certificates of the system: about 17 ms each time, and
    Silence opens a connection for each query. The context of that mode is created once and reused
    (a context may be shared by connections and threads). If PyMySQL changed that private method,
    this one would no longer be called, and each connection would create its own context again.'''
    _default_ctx = None
    _ctx_lock = threading.Lock()

    def _create_ssl_ctx(self, sslp):
        if sslp != {}:  # Explicit TLS options: as PyMySQL does
            return super()._create_ssl_ctx(sslp)
        with _Connection._ctx_lock:
            if _Connection._default_ctx is None:
                _Connection._default_ctx = super()._create_ssl_ctx(sslp)
            return _Connection._default_ctx


def get_conn(db_conn=None, with_database=True, autocommit=False):
    '''Opens a new connection with the project's settings (or the given ones, as DB_CONN). Without
    the database: to list the databases, or to drop and create it'''
    c = db_conn or settings.DB_CONN
    return _Connection(
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
