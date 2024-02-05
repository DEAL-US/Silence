from silence.settings import settings
from silence.db.connector import get_conn

###############################################################################
# Reads and executes the SQL scripts needed to create the database
# and fill it with data, as defined in the settings.
###############################################################################

def create_database():
    conn = get_conn()
    cursor = conn.cursor()
    db_name = settings.DB_CONN["database"]

    cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
    cursor.execute(f"CREATE DATABASE `{db_name}`")
    conn.commit()
    
    for script in settings.SQL_SCRIPTS:
        cursor.execute(f"USE `{db_name}`")
        print_str = f"Executing {script}:"
        print_aux_len = len(print_str) + 2

        print("=" * print_aux_len)
        print(f" {print_str} ")
        print("=" * print_aux_len, "\n")

        with open(f"sql/{script}", "r", encoding="utf-8") as f:
            stmt = ""
            delimiter = ";"
            for line in f:
                if not line or line.strip() == "": 
                    continue  # Skip blank lines
                
                # Emulate the DELIMITER sentence
                if "DELIMITER" in line.upper():
                    delimiter = line.split(" ")[1].strip()
                else:
                    if delimiter in line.upper():
                        if delimiter != ";": 
                            stmt += line.replace(delimiter, ";")
                        else: 
                            stmt += line

                        print(stmt)
                        cursor.execute(stmt)
                        stmt = ""
                    else:
                        stmt += line

        # Commit after every SQL script
        conn.commit()

    # after all database schema is created, we rename all columns and tables to be fully lowercase, this way we avoid any linux/windows weirdness.
    # there's a custom option when installing mysql server, it forces tablenames to be lowercase, maybe include that in the curriculum?
    
    get_table_names_q =  f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA= '{db_name}';"

    cursor.execute(get_table_names_q)
    all_created_tables = cursor.fetchall()
    
    for table_name_tuple in all_created_tables:
        table_name = table_name_tuple[0]

        get_column_names_q = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'"
        cursor.execute(get_column_names_q)

        # table_column_names = cursor.fetchall()

        # for column_name_tuple in table_column_names:
        #     column_name = column_name_tuple[0]

        #     THIS STATEMENT REQUIRES THE NEW TYPE TO BE SPECIFIED, WHICH MIGHT BE A PROBLEM SINCE IT IS HARD TO GET I GUESS.
        #     rename_table_q = f"ALTER TABLE '{table_name}' CHANGE '{column_name}' '{column_name.lower()}' INT(11) NOT NULL;"
        #     cursor.execute(rename_table_q)

        rename_table_q =  f"ALTER TABLE {table_name} RENAME {table_name.lower()};"
        cursor.execute(rename_table_q)

    conn.commit()
    # Clean up when we're done
    cursor.close()