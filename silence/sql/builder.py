from pypika import Table, Field
from pypika import MySQLQuery as Query

def get_login_query(table_name, id_name, id_value):
    users = Table(table_name)
    q = Query.from_(users).select('*').where(users[id_name] == id_value)
    return str(q)

def get_register_user_query(table_name, user):
    field_names = tuple(k for k in user)
    field_values = tuple(user[k] for k in field_names)

    users = Table(table_name)
    q = Query.into(users).columns(*field_names).insert(*field_values)
    return str(q)
