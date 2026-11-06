import json
import os
import pprint
from copy import deepcopy
from secrets import token_urlsafe

###############################################################################
# Project settings, stored in the project's silence.json.
#
# The student never needs to edit silence.json: the admin panel writes it.
# The settings are exposed as uppercase attributes (settings.DB_CONN,
# settings.HTTP_PORT...) and can be changed and saved while Silence runs.
#
# Keep the imports of other Silence modules out of this file's header: almost
# every module imports the settings, so doing so would cause circular imports.
###############################################################################

PROJECT_FILE = "silence.json"

# Default contents of silence.json
DEFAULT_PROJECT = {
    # Version of the format of silence.json
    "version": 3,
    "server": {
        "address": "127.0.0.1",  # Listen only on localhost by default
        "port": 8080,
        "api_prefix": "/api",
        "open_browser": True,
    },
    "database": {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "iissi_user",
        "password": "iissi$user",
        "name": "",
    },
    "auth": {
        # Table and columns of the application's users (empty: not linked)
        "table": "",
        "identifier": "",
        "password": "",
        "role": "",
        "active": "",
        # "argon2": passwords are stored as argon2 hashes; "plain": as text
        "password_mode": "argon2",
        "login": True,
        "register": True,
        "default_role": "",
        "token_max_age": 86400,
    },
    # The JS modules that call the endpoints, generated with them (each template
    # says where it wants them, or disables them)
    "js_api": {
        "enabled": True,
        "dir": "web/js/api/_auto",
    },
    "debug": False,
    "secret_key": "",
}

# Settings that are not stored in silence.json
FIXED_SETTINGS = {
    "COLORED_OUTPUT": True,
    "DECIMALS_AS_STRINGS": False,
    "HTTP_CACHE_TIME": 0,
    "CHECK_FOR_UPDATES": True,
    "CHECK_USER_IS_ACTIVE": True,
    "DEFAULT_ACTIVE_STATUS": True,
    "GITHUB_TEMPLATES_OWNER": "IISSI-US",
    "TEMPLATE_PREFIX": "silence-template-v3-",
    "DEFAULT_TEMPLATE_NAME": "ez-ui",
    "ADMIN_PANEL_REPO": "silence-admin-panel",
}


def merge(defaults, values):
    '''Recursively fills the missing keys of values with the defaults'''
    res = deepcopy(defaults)
    for key, value in (values or {}).items():
        if isinstance(value, dict) and isinstance(res.get(key), dict):
            res[key] = merge(res[key], value)
        else:
            res[key] = value
    return res


def unknown_keys(defaults, values, prefix=""):
    '''Keys of values that do not exist in the defaults, as "section.key"'''
    res = []
    for key, value in (values or {}).items():
        if key not in defaults:
            res.append(prefix + key)
        elif isinstance(value, dict) and isinstance(defaults[key], dict):
            res += unknown_keys(defaults[key], value, prefix + key + ".")
    return res


class Settings:
    def __init__(self, project_dir=None):
        self.load(project_dir)

    def load(self, project_dir=None):
        '''(Re)loads silence.json from the project's folder (by default, the current one)'''
        self.PROJECT_DIR = os.path.abspath(project_dir or os.getcwd())
        self.PROJECT_PATH = os.path.join(self.PROJECT_DIR, PROJECT_FILE)
        self.IS_PROJECT = os.path.isfile(self.PROJECT_PATH)
        self.unknown_settings = []

        values = {}
        if self.IS_PROJECT:
            with open(self.PROJECT_PATH, encoding="utf8") as f:
                values = json.load(f)
            self.unknown_settings = unknown_keys(DEFAULT_PROJECT, values)

        self.project = merge(DEFAULT_PROJECT, values)
        self.apply()

    def apply(self):
        '''Exposes the project's values as the uppercase attributes used by Silence'''
        for key, value in FIXED_SETTINGS.items():
            setattr(self, key, value)

        p = self.project
        server, db, auth = p["server"], p["database"], p["auth"]
        self.DEBUG_ENABLED = bool(p["debug"])
        self.SECRET_KEY = p["secret_key"]
        self.LISTEN_ADDRESS = server["address"]
        # silence run --port wins over silence.json, also after reloading it
        self.HTTP_PORT = getattr(self, "port_override", None) or int(server["port"])
        self.API_PREFIX = "/" + server["api_prefix"].strip("/")
        self.OPEN_BROWSER = bool(server["open_browser"])
        self.DB_CONN = {
            "host": db["host"],
            "port": int(db["port"]),
            "username": db["user"],
            "password": db["password"],
            "database": db["name"],
        }
        self.USER_AUTH_DATA = {
            "table": auth["table"],
            "identifier": auth["identifier"],
            "password": auth["password"],
            "role": auth["role"],
            "active_status": auth["active"],
        }
        self.AUTH_LINKED = bool(auth["table"] and auth["identifier"] and auth["password"])
        self.PASSWORD_MODE = auth["password_mode"]
        self.ALLOW_CLEAR_PASSWORDS = auth["password_mode"] == "plain"
        self.ENABLE_LOGIN = bool(auth["login"]) and self.AUTH_LINKED
        self.ENABLE_REGISTER = bool(auth["register"]) and self.AUTH_LINKED
        self.DEFAULT_ROLE_REGISTER = auth["default_role"] or None
        self.MAX_TOKEN_AGE = int(auth["token_max_age"])
        self.JS_API_ENABLED = bool(p["js_api"]["enabled"])
        self.JS_API_DIR = p["js_api"]["dir"]

    def update(self, section, values):
        '''Changes some values of a section (or a top-level key) and saves silence.json'''
        if section in self.project and isinstance(self.project[section], dict):
            known = {k: v for k, v in values.items() if k in DEFAULT_PROJECT[section]}
            self.project[section].update(known)
        elif section in DEFAULT_PROJECT:
            self.project[section] = values
        else:
            raise KeyError(f"Unknown settings section '{section}'")
        self.apply()
        self.save()

    def save(self):
        with open(self.PROJECT_PATH, "w", encoding="utf8") as f:
            json.dump(self.project, f, indent=4, ensure_ascii=False)
            f.write("\n")

    def warn_unknown_settings(self):
        from silence.logging.default_logger import logger
        if self.unknown_settings:
            logger.warning(f"The following keys in {PROJECT_FILE} are unknown and will be "
                           "ignored: " + ", ".join(self.unknown_settings))

    def __str__(self):
        return pprint.pformat(self.project)


def new_project_data():
    '''Contents of silence.json for a new project'''
    data = deepcopy(DEFAULT_PROJECT)
    data["secret_key"] = token_urlsafe(32)
    return data


settings = Settings()
