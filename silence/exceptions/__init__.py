###############################################################################
# Exceptions used throughout the framework.
# They're very simple so we'll just keep them here for convenience.
###############################################################################

# Something blew up in the database
class DatabaseError(Exception):
    pass