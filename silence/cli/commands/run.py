from silence.server import manager as server_manager
from silence.logging.default_logger import logger
from silence.settings import settings
from silence import __version__


def handle(argv):
    logger.info(f"Silence v{__version__}")
    logger.debug("Current settings:\n" + str(settings))
    server_manager.setup()
    server_manager.run()