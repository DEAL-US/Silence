from flask import jsonify

###############################################################################
# Exceptions used throughout the framework.
# They're very simple so we'll just keep them here for convenience.
###############################################################################

# Something blew up in the database
class DatabaseError(Exception):
    pass

# A SQL string may not be correct
class SQLWarning(Warning):
    pass

# Generic warnings for endpoint creation
class EndpointWarning(Warning):
    pass

# Generic errors for endpoint creation
class EndpointError(Exception):
    pass

# Generic HTTP errors
# Grabbed from https://flask.palletsprojects.com/en/1.1.x/patterns/apierrors/
class HTTPError(Exception):
    def __init__(self, status_code, message=None, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message or f"Error {self.status_code}"
        rv['code'] = self.status_code
        return rv