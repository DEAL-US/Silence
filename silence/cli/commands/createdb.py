import sys

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger
import pymysql

from silence.db.connector import get_conn, error_message

###############################################################################
# silence createdb: creates the database again (DROP and CREATE) and runs the
# scripts of sql/ listed in silence.json (database.scripts), in order, as in
# Silence 2 (SQL_SCRIPTS). The same code as POST /_silence/v1/database/reload
# (Reload, in the admin panel). The database does not need to exist before.
###############################################################################

def handle(args):
    settings.require_project()
    if not settings.DB_CONN["database"]:
        logger.error("There is no database in %s (database.name): set it there or in the admin panel.", PROJECT_FILE)
        sys.exit(1)
    if not settings.project["database"].get("scripts"):
        logger.error('List the scripts of sql/ in %s, in the order to run them: "database": {"scripts": '
                     '["create_tables.sql", "populate.sql"]} (or in the admin panel).', PROJECT_FILE)
        sys.exit(1)
    try:
        get_conn(with_database=False).close()
        error = None
    except pymysql.MySQLError as exc:
        error = error_message(exc)
    if error:
        logger.error("Cannot connect to MariaDB (%s): check the database settings of %s.", error, PROJECT_FILE)
        sys.exit(1)

    from silence.db import scripts
    logger.info("Creating the database %s again...", settings.DB_CONN["database"])
    try:
        done = scripts.reload()
    except scripts.ScriptError as exc:
        for d in exc.done:
            logger.info("    · %s: %d statements", d["file"], d["statements"])
        logger.error("%s", exc)
        if exc.statement:
            logger.error("    %s", exc.statement.strip().splitlines()[0][:200])
        sys.exit(1)
    for d in done:
        logger.info("    · %s: %d statements", d["file"], d["statements"])
    logger.info("Done!")
