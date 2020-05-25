SELECT = "select"
INSERT = "insert"
UPDATE = "update"
DELETE = "delete"
OTHER = "other"

# Returns the SQL operation for a given string
def get_sql_op(sql):
    first_token = sql.strip().split(" ")[0].lower()

    known_ops = {
        "select": SELECT,
        "insert": INSERT,
        "update": UPDATE,
        "delete": DELETE
    }

    return known_ops.get(first_token, OTHER)