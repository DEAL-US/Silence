import sqlvalidator

def sql_is_ok(sql):
    parsed = sqlvalidator.parse(sql)
    return parsed.is_valid()
