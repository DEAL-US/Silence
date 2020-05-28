from pymysql.cursors import DictCursor

from silence.db.connector import get_conn
from silence.exceptions import DatabaseError
from silence.decorators import db_call

###############################################################################
# The DAL (Data Access Layer) functions provide an abstraction layer
# for querying and updating the database.
###############################################################################

# Query method to retrieve information
def query(q, params=None):
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
        return res
    except Exception as exc:
        # If anything happens, wrap the exceptions in a DatabaseError
        raise DatabaseError(exc) from exc
    finally:
        # Close the cursor
        cursor.close()


# Update method to modify information
def update(q, params=None):
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
        return cursor.lastrowid
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
