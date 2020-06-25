from silence.db.dal import query

global TABLE_COLUMNS
TABLE_COLUMNS = {}

# Returns the list of names for the columns of a table, storing it
# after the first query for a given table
def get_table_cols(table_name):
    global TABLE_COLUMNS

    if table_name not in TABLE_COLUMNS:
        cols = query(f"SHOW COLUMNS FROM {table_name}")
        col_names = [col["Field"] for col in cols]
        TABLE_COLUMNS[table_name] = col_names
    
    return TABLE_COLUMNS[table_name]
