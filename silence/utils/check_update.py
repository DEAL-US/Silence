import requests

from silence.settings import settings
from silence.logging.default_logger import logger
from silence import __version__

def check_for_new_version():
    if not settings.CHECK_FOR_UPDATES: return False

    logger.debug("Checking for new updates...")

    try:
        data = requests.get("https://pypi.org/pypi/Silence/json").json()
        latest_version = data["info"]["version"]
    except Exception as exc:
        logger.debug("Exception occurred when checking for updates (muted):")
        logger.debug(str(exc))
        return False

    current_version = __version__.split("-")[0]
    if current_version != latest_version:
        logger.debug("New version available")
        return latest_version
    else:
        logger.debug("Running latest version")
        return False
