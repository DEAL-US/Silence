from silence.db.dal import query

from silence.logging.default_logger import logger

# Caches the columns of a table, to avoid repetitive queries
global TABLE_COLUMNS
TABLE_COLUMNS = {}

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
    tables = get_tables()
    t_pure = next(t for t in get_tables() if t.lower() == table_name.lower())
    primary = query(f"SHOW KEYS FROM {t_pure} WHERE Key_name = 'PRIMARY'")
    return primary[0]['Column_name']

# Returns the list of names for the columns of a table, storing it
# after the first query for a given table
def get_table_cols(table_name):
    global TABLE_COLUMNS

    if table_name not in TABLE_COLUMNS:
        cols = query(f"SHOW COLUMNS FROM {table_name}")
        col_names = [col["Field"] for col in cols]
        TABLE_COLUMNS[table_name] = col_names
    
    return TABLE_COLUMNS[table_name]

