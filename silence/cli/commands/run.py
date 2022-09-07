from silence.logging.default_logger import logger
from silence.settings import settings
from silence.utils.check_update import check_for_new_version
from silence import __version__


def handle(args):
    from silence.server import manager as server_manager
    
    logger.info("Silence v%s", __version__)
    logger.debug("Current settings:\n%s", str(settings))

    new_ver = check_for_new_version()
    if new_ver:
        logger.warning("A new Silence version (v%s) is available. Run 'pip install --upgrade Silence' to upgrade.", new_ver)
        logger.warning("To see what's new, visit: https://github.com/DEAL-US/Silence/blob/master/CHANGELOG.md")

    server_manager.setup()
    server_manager.run()