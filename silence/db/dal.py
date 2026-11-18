import threading
from contextlib import contextmanager

from pymysql.cursors import DictCursor

from silence.db.connector import get_conn
from silence.exceptions import DatabaseError
from silence.logging.default_logger import logger

###############################################################################
# The DAL (Data Access Layer) functions provide an abstraction layer
# for querying and updating the database.
#
# Each query opens its own connection, so that nothing of a request (session
# variables, the isolation level...) reaches another one. Silence's own work
# that runs many queries in a row (reading the schema, generating the tests)
# runs them in a batch: one connection for all of them (see batch()).
###############################################################################

_local = threading.local()  # The connection of the batch of this thread, if any


@contextmanager
def batch():
    '''Runs the queries inside it with one connection (of this thread), instead of one each. Each
    query is still committed (or rolled back) on its own. Nested batches use the outer one'''
    if getattr(_local, "conn", None) is not None:
        yield
        return
    _local.conn = get_conn()
    try:
        yield
    finally:
        conn, _local.conn = _local.conn, None
        conn.close()


def _run(q, params, fetch):
    kept = getattr(_local, "conn", None)
    conn = kept or get_conn()
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
        if conn is not kept:
            conn.close()


def query(q, params=None):
    '''Runs a query and returns its rows as a list of dicts'''
    logger.debug('Executing SQL query "%s" with params %s', q, params)
    return _run(q, params, fetch=True)


def update(q, params=None):
    '''Runs an operation and returns {"lastId": ..., "affectedRows": ...}'''
    logger.debug('Executing SQL operation "%s" with params %s', q, params)
    return _run(q, params, fetch=False)
