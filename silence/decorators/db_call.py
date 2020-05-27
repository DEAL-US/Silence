from functools import wraps
from silence.exceptions import HTTPError, DatabaseError

import re

regex_error_str = re.compile(r"\(.*?, '(.*)'\)")

# Wraps a DB query/update call to catch any possible DatabaseErrors
# and wrap them inside a HTTPError
def db_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DatabaseError as dberr:
            # Grab the error message from the exception
            m = regex_error_str.match(str(dberr))
            msg = m.group(1) if m else str(dberr)
            code = 400
            raise HTTPError(code, msg)
    return wrapper