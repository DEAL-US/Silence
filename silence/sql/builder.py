from pypika import Table, Field
from pypika import MySQLQuery as Query

def get_login_query(table_name, id_name, id_value):
    users = Table(table_name)
    q = Query.from_(users).select('*').where(users[id_name] == id_value)
    return str(q)
