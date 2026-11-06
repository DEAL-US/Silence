###############################################################################
# Exceptions used throughout the framework.
###############################################################################

# Something blew up in the database
class DatabaseError(Exception):
    pass

# Errors in the endpoint definitions (endpoints/*.json)
class EndpointError(Exception):
    pass

# Errors in the test definitions (tests/*.json)
class TestDefinitionError(Exception):
    pass

# Errors for checking session tokens
class TokenError(Exception):
    pass

# Generic HTTP errors, returned to the client as {"message": ..., "code": ...}
class HTTPError(Exception):
    def __init__(self, status_code, message=None, exc_class=None, payload=None):
        Exception.__init__(self, message)
        self.message = message
        self.status_code = status_code
        self.exception = exc_class
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message or f"Error {self.status_code}"
        rv["code"] = self.status_code
        if self.exception:
            rv["exception"] = self.exception
        return rv
