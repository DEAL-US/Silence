from pymysql.cursors import DictCursor

from silence.db.connector import get_conn
from silence.exceptions import DatabaseError
from silence.logging.default_logger import logger

###############################################################################
# The DAL (Data Access Layer) functions provide an abstraction layer
# for querying and updating the database.
###############################################################################

def _run(q, params, fetch):
    conn = get_conn()
    cursor = conn.cursor(DictCursor)
    try:
        cursor.execute(q, params or None)
        if fetch:
            res = cursor.fetchall()
            res = list(res) if res else []
        else:
            res = {"lastId": cursor.lastrowid, "affectedRows": cursor.rowcount}
            # A CALL may return a result set
            if cursor.description:
                res["rows"] = list(cursor.fetchall())
        conn.commit()
        return res
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(exc) from exc
    finally:
        cursor.close()
        conn.close()


def query(q, params=None):
    '''Runs a query and returns its rows as a list of dicts'''
    logger.debug('Executing SQL query "%s" with params %s', q, params)
    return _run(q, params, fetch=True)


def update(q, params=None):
    '''Runs an operation and returns {"lastId": ..., "affectedRows": ...}'''
    logger.debug('Executing SQL operation "%s" with params %s', q, params)
    return _run(q, params, fetch=False)
