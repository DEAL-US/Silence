from pymysql.cursors import DictCursor

from silence.db.connector import get_conn
from silence.exceptions import DatabaseError
from silence.decorators import db_call
from silence.logging.default_logger import logger

###############################################################################
# The DAL (Data Access Layer) functions provide an abstraction layer
# for querying and updating the database.
###############################################################################

# Query method to retrieve information
def query(q, params=None):
    logger.debug(f'Executing SQL query "{q}" with params {params}')

    # Fetch the connection and get a cursor
    conn = get_conn()
    cursor = conn.cursor(DictCursor)
    try:
        # Execute the query, with or without parameters and return the result
        if params:
            cursor.execute(q, params)
        else:
            cursor.execute(q)

        res = cursor.fetchall()
        logger.debug(f"Query result: {res}")
        return res
    except Exception as exc:
        # If anything happens, wrap the exceptions in a DatabaseError
        raise DatabaseError(exc) from exc
    finally:
        # Close the cursor
        cursor.close()


# Update method to modify information
def update(q, params=None):
    logger.debug(f'Executing SQL operation "{q}" with params {params}')
    conn = get_conn()
    cursor = conn.cursor(DictCursor)

    # Fetch the connection and get a cursor
    try:
        # Execute the query, with or without parameters and return the result
        if params:
            cursor.execute(q, params)
        else:
            cursor.execute(q)

        conn.commit()

        # Return the ID of the row that was modified or inserted
        res = cursor.lastrowid
        logger.debug(f"Last modified row ID: {res}")
        return res
    except Exception as exc:
        # If anything happens, wrap the exceptions in a DatabaseError
        raise DatabaseError(exc) from exc
    finally:
        # Close the cursor
        cursor.close()

###############################################################################
# Safe wrappers for the API, which return an HTTPError instead of a
# DatabaseError
###############################################################################

@db_call
def api_safe_query(*args, **kwargs):
    return query(*args, **kwargs)

@db_call
def api_safe_update(*args, **kwargs):
    return update(*args, **kwargs)
