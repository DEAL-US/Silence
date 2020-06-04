###############################################################################
# Default settings, which can be overriden by each individual project.
###############################################################################

DEBUG_ENABLED = False
HTTP_PORT = 8080
API_PREFIX = ""

RUN_API = True
RUN_WEB = True

DB_CONN = {
    "host": "localhost",
    "port": 3306,
    "username": "default_username",
    "password": "default_password",
    "database": "default_database",
}

DB_CONN_POOL_SIZE = 50

USER_AUTH_DATA = {
    "table": "users",
    "identifier": "username",
    "password": "password",
}

SECRET_KEY = "These are generated automatically for each project."
MAX_TOKEN_AGE = 86400

SQL_SCRIPTS = []

PROJECT_TEMPLATE_NAME = "silence-app"
PROJECT_TEMPLATE_REPO = "https://github.com/agu-borrego/Silence-project-template.git"

ENABLE_LOGIN = True
ENABLE_REGISTER = True
