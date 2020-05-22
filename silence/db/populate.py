from silence.settings import settings
from silence.db.connector import get_conn

###############################################################################
# Reads and executes the SQL scripts needed to create the database
# and fill it with data, as defined in the settings.
###############################################################################

def create_database():
    conn = get_conn()
    cursor = conn.cursor()
    
    for script in settings.SQL_SCRIPTS:
        print_str = f"Executing {script}:"
        print_aux_len = len(print_str) + 2

        print("=" * print_aux_len)
        print(f" {print_str} ")
        print("=" * print_aux_len, "\n")

        with open(f"sql/{script}", "r", encoding="utf-8") as f:
            stmt = ""
            delimiter = ";"
            for line in f:
                if not line or line.strip() == "": continue  # Skip blank lines
                
                # Emulate the DELIMITER sentence
                if "DELIMITER" in line.upper():
                    delimiter = line.split(" ")[1].strip()
                else:
                    if delimiter in line.upper():
                        if delimiter != ";": stmt += line.replace(delimiter, ";")
                        else: stmt += line

                        print(stmt)
                        cursor.execute(stmt)
                        stmt = ""
                    else:
                        stmt += line

        # Commit after every SQL script
        conn.commit()
    # Clean up when we're done
    cursor.close()