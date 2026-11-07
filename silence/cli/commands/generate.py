import sys

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.db.connector import test_connection

###############################################################################
# silence createapi [table...]: endpoints/auto_<table>.json and the JS API
# silence createtests [table...] [--http]: tests/auto_<table>.json (and the
#     .http files for VS Code's REST Client)
# silence hash <password>: the argon2 hash of a password
# The same code as the admin API (POST /_silence/v1/endpoints/generate...).
###############################################################################

def require_project():
    if not settings.IS_PROJECT:
        logger.error("There is no %s here: run this command in the folder of a Silence project.", PROJECT_FILE)
        sys.exit(1)
    settings.require_valid()
    error = test_connection(settings.DB_CONN) if settings.DB_CONN["database"] else "no database selected"
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
    logger.info("Endpoints written in endpoints/auto_<table>.json.")
    from silence.server.endpoints import REGISTRY
    REGISTRY.log_errors()


def createtests(args):
    require_project()
    from silence.server import manager
    from silence.testing import generator, http_export
    manager.setup()
    try:
        res = generator.generate(args.tables or None)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)
    for t in res["tables"]:
        logger.info("    · %s: %d tests", t["table"], t["tests"])
    logger.info("Tests written in tests/auto_<table>.json; run them from the admin panel, or export them with --http.")
    if args.http:
        for f in http_export.export(args.tables or None)["files"]:
            logger.info("    · %s", f)
        logger.info("Open them in VS Code with the REST Client extension. Sending them CHANGES the database.")


def hash_password(args):
    from silence.auth.passwords import _hasher
    print(_hasher.hash(args.password))
