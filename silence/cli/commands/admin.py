import sys

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.cli.template_downloader import DownloadError
from silence.cli.commands.new import install_admin_panel, panel_version

###############################################################################
# silence admin update: installs (or updates) the admin panel of the project,
# in its admin/ folder, from the repo silence-admin-panel.
###############################################################################

def handle(args):
    if not settings.IS_PROJECT:
        logger.error("There is no %s here: run this command in the folder of a Silence project.", PROJECT_FILE)
        sys.exit(1)
    before = panel_version(settings.PROJECT_DIR)
    try:
        after = install_admin_panel(settings.PROJECT_DIR)
    except DownloadError as exc:
        logger.error("Cannot get the admin panel: %s", exc)
        sys.exit(1)
    old = f"v{before.get('version')}" if before else "none"
    logger.info("Admin panel: %s -> v%s (admin/).", old, (after or {}).get("version", "?"))
