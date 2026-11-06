import requests

from silence.settings import settings
from silence.logging.default_logger import logger
from silence import __version__

import re

def release_tuple(version):
    '''Numeric release part of a version string: "3.0.0.dev0" -> (3, 0, 0)'''
    match = re.match(r"\d+(?:\.\d+)*", version)
    return tuple(int(n) for n in match.group(0).split(".")) if match else ()

def check_for_new_version():
    if not settings.CHECK_FOR_UPDATES: 
        return False

    logger.debug("Checking for new updates...")

    try:
        data = requests.get("https://pypi.org/pypi/Silence/json", timeout=3).json()
        latest_version = data["info"]["version"]
    except Exception as exc:
        logger.debug("Exception occurred when checking for updates (muted):")
        logger.debug(str(exc))
        return False

    if release_tuple(latest_version) > release_tuple(__version__):
        logger.debug("New version available")
        return latest_version
    else:
        logger.debug("Running latest version")
        return False
