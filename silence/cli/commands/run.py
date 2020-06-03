from silence.server import manager as server_manager
from silence.logging.default_logger import logger
from silence import __version__


def handle(argv):
    logger.info(f"Silence v{__version__}")
    server_manager.setup()
    server_manager.run()