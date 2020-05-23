###############################################################################
# Default settings, which can be overriden by each individual project.
###############################################################################

DEBUG_ENABLED = True
HTTP_PORT = 8080
API_PREFIX = ""

DB_CONN = {
    "host": "localhost",
    "port": 3306,
    "username": "default_username",
    "password": "default_password",
    "database": "default_database",
}

SECRET_KEY = "These are generated automatically for each project."

SQL_SCRIPTS = []

PROJECT_TEMPLATE_NAME = "silence-app"
PROJECT_TEMPLATE_REPO = "https://github.com/agu-borrego/Silence-project-template.git"
