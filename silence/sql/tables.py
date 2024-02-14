from silence.db.dal import query

from silence.logging.default_logger import logger

from silence.settings import settings

# Caches the columns of a table, to avoid repetitive queries
global TABLE_COLUMNS
TABLE_COLUMNS = {}

def get_tables():
    res = query(q = "SHOW FULL TABLES WHERE table_type = 'BASE TABLE';")
    tables = {}
    for table_data in res:
        # Grab the value that is not "BASE TABLE", which will be the name of the table
        table_name = next(x for x in table_data.values() if x != "BASE TABLE")
        tables[table_name] = get_table_cols(table_name)

    logger.debug("Tables in database: %s", str(tables))
    return tables

def get_views():
    res = query(q = "SHOW FULL TABLES WHERE table_type = 'VIEW';")
    views = {}
    for view_data in res:
        # Grab the value that is not "VIEW", which will be the name of the view
        view_name = next(x for x in view_data.values() if x != "VIEW")
        views[view_name] = get_table_cols(view_name)

    logger.debug("Views in database: %s", str(views))
    return views

def get_primary_key(table_name):
    t_pure = next(t for t in get_tables() if t.lower() == table_name.lower())
    primary = query(f"SHOW KEYS FROM {t_pure} WHERE Key_name = 'PRIMARY'")
    
    if primary:
        return primary[0]['Column_name']
    else:
        return None

def get_primary_key_views(view_name):
    all_primary_keys = []
    for table in get_tables():
        pk = get_primary_key(table)
        if pk:
            all_primary_keys.append(pk)
    
    primary_keys = []
    view_columns = query(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{settings.DB_CONN['database']}' AND TABLE_NAME = '{view_name}'")
    for v in view_columns:
        if(v["COLUMN_NAME"] in all_primary_keys):
            primary_keys.append(v["COLUMN_NAME"])

    return primary_keys

def is_auto_increment(table_name, column_name):
    auto = query(f"SELECT EXTRA FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{settings.DB_CONN['database']}' AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column_name}'")
    res = auto[0]['EXTRA'] == 'auto_increment'
    return res

# Returns the list of names for the columns of a table, storing it
# after the first query for a given table
def get_table_cols(table_name):
    global TABLE_COLUMNS

    if table_name not in TABLE_COLUMNS:
        cols = query(f"SHOW COLUMNS FROM {table_name}")
        col_names = [col["Field"] for col in cols]
        TABLE_COLUMNS[table_name] = col_names
    
    return TABLE_COLUMNS[table_name]
