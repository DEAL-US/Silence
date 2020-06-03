import pymysql

from silence.settings import settings

###############################################################################
# The connector fetches the relevant configuration parameters
# and uses them to build a connection to the database.
###############################################################################

global conn
conn = None

def get_conn():
    # Only connect lazily
    global conn
    if conn is None:
        conn = pymysql.connect(
            host=settings.DB_CONN["host"],
            port=settings.DB_CONN["port"],
            user=settings.DB_CONN["username"],
            password=settings.DB_CONN["password"],
            database=settings.DB_CONN["database"],
        )
    return conn

