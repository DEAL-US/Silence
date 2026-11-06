import os
import socket
import sys
import threading
import webbrowser

from silence.logging.default_logger import logger
from silence.settings import settings, PROJECT_FILE
from silence.utils.check_update import check_for_new_version
from silence.db.connector import test_connection
from silence import __version__

###############################################################################
# silence run: starts the API, the web app, the admin API and the admin panel
# (if the project has one), watches the project's files and opens the panel.
###############################################################################

def port_in_use(address, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((address, port))
            return False
        except OSError:
            return True


def check_panel():
    '''Warns if the admin panel needs another version of the admin API'''
    from silence.cli.commands.new import panel_version
    from silence.manage.api import API_VERSION
    panel = panel_version(settings.PROJECT_DIR)
    if panel is None:
        return False
    if panel.get("api") != API_VERSION:
        logger.warning("The admin panel (v%s) needs version %s of the admin API, and this Silence has "
                       "version %s: run 'silence admin update' (or update Silence).",
                       panel.get("version"), panel.get("api"), API_VERSION)
    return True


def handle(args):
    if not settings.IS_PROJECT:
        logger.error("There is no %s here: run this command in the folder of a Silence project "
                     "(create one with 'silence new <name>').", PROJECT_FILE)
        sys.exit(1)

    if args.port:
        settings.port_override = args.port
        settings.HTTP_PORT = args.port
    if port_in_use(settings.LISTEN_ADDRESS, settings.HTTP_PORT):
        logger.error("The port %d is in use (another 'silence run'?). Stop it or choose another one "
                     "with 'silence run --port 8081'.", settings.HTTP_PORT)
        sys.exit(1)

    from silence.server import manager as server_manager, watcher

    logger.info("Silence v%s", __version__)
    settings.warn_unknown_settings()
    new_ver = check_for_new_version()
    if new_ver:
        logger.warning("A new Silence version (v%s) is available.", new_ver)

    db_error = test_connection(settings.DB_CONN) if settings.DB_CONN["database"] else "no database selected"
    server_manager.setup()
    has_panel = check_panel()
    if db_error:
        where = "the admin panel" if has_panel else PROJECT_FILE
        logger.warning("The database is not configured yet (%s): set it up in %s.", db_error, where)
    else:
        server_manager.print_endpoints()
    watcher.start()

    base = f"http://{settings.LISTEN_ADDRESS}:{settings.HTTP_PORT}"
    logger.info("Web app:      %s/", base)
    logger.info("API:          %s%s", base, settings.API_PREFIX)
    if has_panel:
        logger.info("Admin panel:  %s/admin/", base)
    logger.info("")

    # In a remote session (SSH) there is no browser here: the URL is enough
    # (VS Code forwards the port and opens it)
    remote = bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"))
    if has_panel and settings.OPEN_BROWSER and not args.no_browser and not remote:
        threading.Timer(1.0, lambda: webbrowser.open(f"{base}/admin/")).start()

    server_manager.run()
