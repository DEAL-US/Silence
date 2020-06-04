from random import choice
import pymysql

from silence.settings import settings

###############################################################################
# The connector fetches the relevant configuration parameters
# and uses them to build a connection to the database.
###############################################################################

global conn_pool
conn_pool = None

def get_conn():
    # Create the pool of connections lazily
    global conn_pool
    if conn_pool is None:
        conn_pool = [pymysql.connect(
                        host=settings.DB_CONN["host"],
                        port=settings.DB_CONN["port"],
                        user=settings.DB_CONN["username"],
                        password=settings.DB_CONN["password"],
                        database=settings.DB_CONN["database"],
                    ) for _ in range(settings.DB_CONN_POOL_SIZE)]
    return choice(conn_pool)
