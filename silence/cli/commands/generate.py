import sys

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.db.connector import connection_error
from silence.auth.passwords import argon2_hash

###############################################################################
# silence createapi [table...]: endpoints/auto_<table>.json, their tests (tests/auto_<table>.json)
# and the JS API
# silence hash <password>: the argon2 hash of a password
# createapi runs the same code as the admin API (POST /_silence/v1/endpoints/generate).
###############################################################################

def require_project():
    settings.require_project()
    error = connection_error()
    if error:
        logger.error("Cannot connect to the database (%s): set it in %s or in the admin panel.", error, PROJECT_FILE)
        sys.exit(1)


def createapi(args):
    require_project()
    from silence.server import generator
    try:
        res = generator.generate(args.tables or None)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)
    for t in res["tables"]:
        kind = "view" if t["view"] else "table"
        custom = f" (custom, not generated: {', '.join(t['custom'])})" if t["custom"] else ""
        logger.info("    · %s %s: %s%s", kind, t["table"], ", ".join(t["generated"]) or "—", custom)
    for f in res["removed"]:
        logger.info("    · removed %s (its table no longer exists)", f)
    logger.info("Endpoints written in endpoints/auto_<table>.json, and their tests in tests/auto_<table>.json.")
    js = res["jsApi"]
    if js["notGenerated"]:
        logger.info("The JS API has not been generated: %s.", js["notGenerated"])
    else:
        logger.info("JS API written in %s/.", js["dir"])
    from silence.server.endpoints import REGISTRY
    REGISTRY.log_errors()


def hash_command(args):
    print(argon2_hash(args.password))
