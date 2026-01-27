import re

def silence_to_mysql(sql):
    return re.sub(r"\$\w+", "%s", sql)