from silence.db.schema import get_schema
from silence.settings import settings

###############################################################################
# The users of the application: the rows of the users table linked in
# silence.json (auth.table). The identifier used to log in (auth.identifier) is
# a column of that table ("email") or of a table that it references with a
# foreign key ("people.email": the users table has an FK to people), as when
# the credentials are in their own table and the email is in the people's one:
#
#   credentials(person_id → people.person_id, password, role)
#   people(person_id, email, ...)
#
# Then the users are read joining both tables, and the identifier comes in each
# row with its column's name ("email").
###############################################################################


class UsersTableError(Exception):
    pass


def identifier_parts():
    '''(table, column) of the identifier; table is None if it is a column of the users table'''
    ident = settings.USER_AUTH_DATA["identifier"]
    if "." in ident:
        table, column = ident.split(".", 1)
        return table, column
    return None, ident


def identifier_field():
    '''The name of the identifier in the rows of the users (and in the body of the login)'''
    return identifier_parts()[1]


def identifier_is_external():
    return identifier_parts()[0] is not None


def join_of(users_rel, table):
    '''The foreign key of the users table to another table: (column, referenced column)'''
    for fk in users_rel.fks:
        if fk["refTable"].lower() == table.lower():
            return fk["column"], fk["refColumn"]
    raise UsersTableError(f"the users table {users_rel.name} has no foreign key to {table}, "
                          f"where the identifier ({settings.USER_AUTH_DATA['identifier']}) is")


def users_select():
    '''The SQL that reads the users (with the identifier, if it is in another table), to which a
    WHERE can be added on "u." (the users table) or on the identifier (identifier_sql())'''
    schema = get_schema()
    users = schema.get(settings.USER_AUTH_DATA["table"])
    if users is None:
        raise UsersTableError(f"the users table '{settings.USER_AUTH_DATA['table']}' does not exist")
    table, column = identifier_parts()
    if table is None:
        return f"SELECT u.* FROM `{users.name}` u"
    rel = schema.get(table)
    if rel is None or rel.column(column) is None:
        raise UsersTableError(f"the identifier {table}.{column} does not exist")
    fk, ref = join_of(users, rel.name)
    col = rel.column(column).name
    return (f"SELECT u.*, i.`{col}` AS `{col}` FROM `{users.name}` u "
            f"JOIN `{rel.name}` i ON u.`{fk}` = i.`{ref}`")


def identifier_sql():
    '''The identifier in the WHERE of users_select()'''
    table, column = identifier_parts()
    return f"i.`{column}`" if table else f"u.`{column}`"
