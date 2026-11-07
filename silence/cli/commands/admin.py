import sys

from silence.settings import settings, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.cli import template_downloader as tpl
from silence.cli.template_downloader import DownloadError
from silence.cli.commands.new import install_admin_panel, panel_version

###############################################################################
# silence admin update [--version <v> | --latest] [--repo <owner/repo>]
# Installs (or updates) the admin panel of the project, in admin/: the one in
# "admin" of silence.json (or the default one of this Silence, if there is
# none), at its version. --version, --latest and --repo change it, and the
# choice is saved in silence.json.
###############################################################################

def handle(args):
    if not settings.IS_PROJECT:
        logger.error("There is no %s here: run this command in the folder of a Silence project.", PROJECT_FILE)
        sys.exit(1)
    settings.require_valid()

    admin = dict(settings.project.get("admin") or tpl.default_admin())
    if args.repo:
        admin["repo"] = args.repo
        if not (args.version or args.latest):
            admin["version"] = tpl.LATEST
    if args.version:
        admin["version"] = args.version
    if args.latest:
        admin["version"] = tpl.LATEST

    before = panel_version(settings.PROJECT_DIR)
    try:
        after = install_admin_panel(settings.PROJECT_DIR, admin["repo"], admin["version"])
    except DownloadError as exc:
        logger.error("Cannot get the admin panel: %s", exc)
        sys.exit(1)
    settings.update("admin", admin)

    old = f"v{before.get('version')}" if before else "none"
    new = f"v{after.get('version')}" if after else "?"
    logger.info("Admin panel %s %s: %s -> %s (admin/; recorded in %s).",
                admin["repo"], admin["version"], old, new, PROJECT_FILE)
