from silence.db.dal import query
from silence.sql.table_cols import get_table_cols

from silence.logging.default_logger import logger

# Returns the list of names for the columns of a table, storing it
# after the first query for a given table
def get_tables():
    res = query(q = "SHOW FULL TABLES WHERE table_type = 'BASE TABLE';")
    tables = {}
    for t in res:
        tables[list(t.values())[0]] = get_table_cols(list(t.values())[0])

    logger.debug(f"tables in database: {tables}")
    return tables

def get_views():
    res = query(q = "SHOW FULL TABLES WHERE table_type = 'VIEW';")
    views = {}
    for v in res:
        views[list(v.values())[0]] = get_table_cols(list(v.values())[0])

    logger.debug(f"views in database: {views}")
    return views
    
def get_primary_key(table_name):
    res = query(q = f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
    return res