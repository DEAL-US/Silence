import json
import os
import re
from copy import deepcopy
from secrets import token_urlsafe

from silence.project.files import write_json

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
        # Shows in the console the body of each POST and PUT to the API (never passwords)
        "log_bodies": True,
        # DECIMAL columns as text ("19.90") instead of numbers, to keep their exact value
        "decimals_as_strings": False,
        # Checks at start whether there is a newer Silence (needs network)
        "check_updates": True,
    },
    "database": {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "iissi_user",
        "password": "iissi$user",
        "name": "",
        # Scripts of sql/ that reload the database (from the admin panel), in order
        "scripts": [],
    },
    "auth": {
        # Table and columns of the application's users (empty: not linked). The identifier may
        # be a column of a table that the users table references: "people.email"
        "table": "",
        "identifier": "",
        "password": "",
        "role": "",
        "active": "",
        # "argon2": passwords are stored as argon2 hashes; "plain": as text
        "password_mode": "argon2",
        "login": True,
        "token_max_age": 86400,
    },
    # The JS modules that call the endpoints, generated with them (each template
    # says where it wants them, or disables them)
    "js_api": {
        "enabled": True,
        "dir": "web/js/api/_auto",
    },
    # The admin panel of the project (admin/): {"repo": "owner/repo", "version": "v1.0.0"};
    # null if it has none or it is not known. silence admin update installs this one
    "admin": None,
    # The template of the front-end it was created from: {"repo": "owner/repo", "version": "v1.1.0"};
    # null if it is not known (written by silence new)
    "template": None,
    "debug": False,
    "secret_key": "",
}

# Settings that are not stored in silence.json
FIXED_SETTINGS = {
    "COLORED_OUTPUT": True,
    "HTTP_CACHE_TIME": 0,
    "CHECK_USER_IS_ACTIVE": True,
    "DEFAULT_ACTIVE_STATUS": True,
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


PASSWORD_MODES = ("argon2", "plain")


def validate(p):
    '''The problems of the values of silence.json (after merging the defaults), as text'''
    errors = []

    def check(section, key, ok, expected):
        value = p[section][key] if section else p[key]
        if not ok(value):
            where = f"{section}.{key}" if section else key
            errors.append(f"{where} must be {expected}, not {json.dumps(value, ensure_ascii=False)}")

    is_str = lambda v: isinstance(v, str)
    is_bool = lambda v: isinstance(v, bool)
    is_port = lambda v: isinstance(v, int) and not isinstance(v, bool) and 0 < v < 65536

    for section in ("server", "database", "auth", "js_api"):
        if not isinstance(p.get(section), dict):
            errors.append(f"{section} must be an object")
    if errors:
        return errors

    check(None, "version", lambda v: v == 3, "3")
    check("server", "address", lambda v: is_str(v) and v != "", "an address (e.g., \"127.0.0.1\")")
    check("server", "port", is_port, "a port number (1-65535)")
    check("server", "api_prefix", lambda v: is_str(v) and v.strip("/") != "" and " " not in v,
          "a URL prefix (e.g., \"/api\")")
    for key in ("open_browser", "log_bodies", "decimals_as_strings", "check_updates"):
        check("server", key, is_bool, "true or false")
    for key in ("host", "user", "password"):
        check("database", key, is_str, "a text")
    check("database", "name", lambda v: is_str(v) and re.fullmatch(r"[\w$]*", v) is not None,
          "the name of a database (letters, digits, _ and $)")
    check("database", "port", is_port, "a port number (1-65535)")
    check("database", "scripts", lambda v: isinstance(v, list) and all(
        is_str(f) and f.endswith(".sql") and "/" not in f and "\\" not in f for f in v),
        'a list of files of sql/ (e.g., ["create_tables.sql", "populate.sql"])')
    for key in ("table", "identifier", "password", "role", "active"):
        check("auth", key, is_str, "a text (\"\" if not used)")
    check("auth", "password_mode", lambda v: v in PASSWORD_MODES, " or ".join(f'"{m}"' for m in PASSWORD_MODES))
    check("auth", "login", is_bool, "true or false")
    check("auth", "token_max_age", lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
          "a number of seconds")
    a = p["auth"]
    if is_str(a.get("table")) and a["table"] and not (a.get("identifier") and a.get("password")):
        errors.append("auth: with a users table, identifier and password are needed")
    check("js_api", "enabled", is_bool, "true or false")
    check("js_api", "dir", lambda v: is_str(v) and ".." not in v.split("/") and not v.startswith("/"),
          "a folder inside the project (e.g., \"web/js/api/_auto\")")
    for key in ("admin", "template"):
        value = p.get(key)
        if value is not None and not (isinstance(value, dict) and isinstance(value.get("repo"), str)
                                      and "/" in value["repo"] and isinstance(value.get("version"), str)):
            errors.append(f'{key} must be null or {{"repo": "owner/repo", "version": "v1.0.0" or "latest"}}, not '
                          + json.dumps(value, ensure_ascii=False))
    check(None, "debug", is_bool, "true or false")
    check(None, "secret_key", lambda v: is_str(v) and v != "", "a text")
    return errors


class Settings:
    def __init__(self, project_dir=None):
        self.load(project_dir)

    def load(self, project_dir=None):
        '''(Re)loads silence.json from the project's folder (by default, the current one)'''
        self.PROJECT_DIR = os.path.abspath(project_dir or os.getcwd())
        self.PROJECT_PATH = os.path.join(self.PROJECT_DIR, PROJECT_FILE)
        self.IS_PROJECT = os.path.isfile(self.PROJECT_PATH)
        self.unknown_settings = []
        self.errors = []

        values = {}
        if self.IS_PROJECT:
            try:
                with open(self.PROJECT_PATH, encoding="utf8") as f:
                    values = json.load(f)
                if not isinstance(values, dict):
                    raise ValueError("it must contain an object")
            except ValueError as exc:
                self.errors = [f"{PROJECT_FILE} is not valid JSON: {exc}"]
                values = None
            if values is not None:
                self.unknown_settings = unknown_keys(DEFAULT_PROJECT, values)

        project = merge(DEFAULT_PROJECT, values) if values is not None else None
        if project is not None:
            self.errors = validate(project)
        if self.errors:
            # Keep the previous values if there are any (a reload while running);
            # otherwise the defaults, and the commands refuse to run (see require_valid)
            if not hasattr(self, "project"):
                self.project = merge(DEFAULT_PROJECT, {})
                self.apply()
            return
        self.project = project
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
        self.LOG_BODIES = bool(server["log_bodies"])
        self.DECIMALS_AS_STRINGS = bool(server["decimals_as_strings"])
        self.CHECK_FOR_UPDATES = bool(server["check_updates"])
        self.DB_CONN = db_conn_of(db)
        self.USER_AUTH_DATA = {
            "table": auth["table"],
            "identifier": auth["identifier"],
            "password": auth["password"],
            "role": auth["role"],
            "active_status": auth["active"],
        }
        self.AUTH_LINKED = bool(auth["table"] and auth["identifier"] and auth["password"])
        self.PASSWORD_MODE = auth["password_mode"]
        self.ENABLE_LOGIN = bool(auth["login"]) and self.AUTH_LINKED
        self.MAX_TOKEN_AGE = int(auth["token_max_age"])
        self.JS_API_ENABLED = bool(p["js_api"]["enabled"])
        self.JS_API_DIR = p["js_api"]["dir"]

    def update(self, section, values):
        '''Changes some values of a section (or a top-level key) and saves silence.json.
        ValueError (with the problems) if the result is not valid: nothing is saved'''
        if section not in DEFAULT_PROJECT:
            raise KeyError(f"Unknown settings section '{section}'")
        new = json.loads(json.dumps(self.project))
        if isinstance(DEFAULT_PROJECT[section], dict):
            new[section].update({k: v for k, v in values.items() if k in DEFAULT_PROJECT[section]})
        else:
            new[section] = values
        errors = validate(new)
        if errors:
            raise ValueError("; ".join(errors))
        self.project = new
        self.errors = []
        self.apply()
        self.save()

    def replace(self, values):
        '''Replaces all of silence.json with values (the secret key is kept) and saves it.
        ValueError (with the problems) if it is not valid: nothing is saved'''
        if not isinstance(values, dict):
            raise ValueError(f"{PROJECT_FILE} must contain an object")
        values = {k: v for k, v in values.items() if k != "secret_key"}
        unknown = unknown_keys(DEFAULT_PROJECT, values)
        if unknown:
            raise ValueError("unknown keys: " + ", ".join(unknown))
        new = merge(DEFAULT_PROJECT, values)
        new["secret_key"] = self.project["secret_key"]
        errors = validate(new)
        if errors:
            raise ValueError("; ".join(errors))
        self.project = new
        self.errors = []
        self.unknown_settings = []
        self.apply()
        self.save()

    def require_valid(self):
        '''Stops the command if silence.json has errors'''
        if self.errors:
            from silence.logging.default_logger import logger
            logger.error("%s has errors:", PROJECT_FILE)
            for err in self.errors:
                logger.error("    · %s", err)
            raise SystemExit(1)

    def require_project(self, hint=""):
        '''Stops the command if it is not run in the folder of a project, or if its silence.json
        has errors'''
        if not self.IS_PROJECT:
            from silence.logging.default_logger import logger
            logger.error("There is no %s here: run this command in the folder of a Silence project%s.",
                         PROJECT_FILE, hint)
            raise SystemExit(1)
        self.require_valid()

    def save(self):
        write_json(self.PROJECT_PATH, self.project)

    def warn_unknown_settings(self):
        from silence.logging.default_logger import logger
        if self.unknown_settings:
            logger.warning(f"The following keys in {PROJECT_FILE} are unknown and will be "
                           "ignored: " + ", ".join(self.unknown_settings))



def db_conn_of(database):
    '''The connection (as DB_CONN: host, port, username, password, database) of a "database"
    section of silence.json'''
    return {"host": database.get("host"), "port": int(database.get("port") or 3306),
            "username": database.get("user"), "password": database.get("password"),
            "database": database.get("name") or None}


def new_project_data():
    '''Contents of silence.json for a new project'''
    data = deepcopy(DEFAULT_PROJECT)
    data["secret_key"] = token_urlsafe(32)
    return data


settings = Settings()
