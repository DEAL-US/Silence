###############################################################################
# Default settings, which can be overriden by each individual project.
###############################################################################

# Shows debug messages while Silence is running
DEBUG_ENABLED = False

# The address and port in which the API and the web server will be deployed
LISTEN_ADDRESS = "0.0.0.0"  # Listen on all interfaces by default
HTTP_PORT = 8080

# The sequence of SQL scripts located in the sql/ folder that must
# be ran when the 'silence createdb' command is issued
SQL_SCRIPTS = []

# The URL prefix for all API endpoints
API_PREFIX = "/api"

# Enables or disables the API and the web server separately
RUN_API = True
RUN_WEB = True

# Database connection details
DB_CONN = {
    "host": "127.0.0.1",
    "port": 3306,
    "username": "default_username",
    "password": "default_password",
    "database": "default_database",
}

# Table and fields that are used for both login and register
USER_AUTH_DATA = {
    "table": "users",
    "identifier": "username",
    "password": "password",
}

# Enables or disables the /login and /register endpoints separately
ENABLE_LOGIN = True
ENABLE_REGISTER = True

# A random string that is used for signing session tokens and also passed to Flask
SECRET_KEY = "These are generated automatically for each project."

# Maximum validity time of a session token in seconds
MAX_TOKEN_AGE = 86400

# Default settings for creating a new project
PROJECT_TEMPLATE_NAME = "silence-app"
PROJECT_TEMPLATE_REPO = "https://github.com/agu-borrego/Silence-project-template.git"
