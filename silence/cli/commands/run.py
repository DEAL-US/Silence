import sys
import threading
import webbrowser

from silence.logging.default_logger import logger
from silence.settings import settings, PROJECT_FILE
from silence.utils.check_update import check_for_new_version
from silence.db.connector import test_connection
from silence import __version__

###############################################################################
# silence run: starts the API, the web app and the admin panel (/admin), and
# opens the panel in the browser.
###############################################################################

def handle(args):
    if not settings.IS_PROJECT:
        logger.error("There is no %s here: run this command in the folder of a Silence project "
                     "(create one with 'silence new <name>').", PROJECT_FILE)
        sys.exit(1)

    if args.port:
        settings.HTTP_PORT = args.port

    from silence.server import manager as server_manager

    logger.info("Silence v%s", __version__)
    settings.warn_unknown_settings()

    new_ver = check_for_new_version()
    if new_ver:
        logger.warning("A new Silence version (v%s) is available.", new_ver)

    base = f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}"
    db_error = test_connection(settings.DB_CONN) if settings.DB_CONN["database"] else "no database selected"
    if db_error:
        logger.warning("The database is not configured yet (%s): set it up in the admin panel.", db_error)
        server_manager.setup()
    else:
        server_manager.setup()
        server_manager.print_endpoints()

    logger.info("Web app:      %s/", base)
    logger.info("API:          %s%s", base, settings.API_PREFIX)
    logger.info("Admin panel:  %s/admin/\n", base)

    if settings.OPEN_BROWSER and not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"{base}/admin/")).start()

    server_manager.run()
