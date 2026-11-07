import pymysql
from pymysql.constants import CLIENT

from silence.settings import settings

###############################################################################
# The connector builds the connections to the database.
###############################################################################


def get_conn(db_conn=None):
    '''Opens a new connection with the project's settings (or the given ones)'''
    c = db_conn or settings.DB_CONN
    return pymysql.connect(
        host=c["host"],
        port=int(c["port"]),
        user=c["username"],
        password=c["password"],
        database=c["database"] or None,
        charset="utf8mb4",
        # rowcount of UPDATE is the number of matched rows, not of changed ones,
        # so that a PUT with the same values is not mistaken for a missing row
        client_flag=CLIENT.FOUND_ROWS,
        connect_timeout=5,
    )


def test_connection(db_conn):
    '''Tries to connect with the given parameters. Returns None if it works,
    or the error message otherwise'''
    try:
        conn = get_conn(db_conn)
        conn.close()
        return None
    except pymysql.MySQLError as exc:
        return exc.args[1] if len(exc.args) > 1 else str(exc)
