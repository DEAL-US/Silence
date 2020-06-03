import importlib

from os import listdir
from os.path import splitext

from silence.server import manager, default_endpoints
from silence.settings import settings
from silence.logging.default_logger import logger

###############################################################################
# Look for .py files inside the project's "/api" folder
# and force them to run, activating the @endpoint decorators
###############################################################################

def load_user_endpoints():
    logger.debug("Looking for custom endpoints...")

    # Load every .py file inside the api/ folder
    for pyfile in listdir("api"):
        module_name = "api." + splitext(pyfile)[0]
        logger.debug(f"Found endpoint file: {module_name}")

        try:
            importlib.import_module(module_name)
        except ImportError:
            raise RuntimeError(f"Could not load the API file {module_name}")
    
###############################################################################
# Register the Silence-provided endpoints
###############################################################################
def load_default_endpoints():
    route_prefix = settings.API_PREFIX
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]

    manager.APP.add_url_rule(f"{route_prefix}/login", "login", default_endpoints.login, methods=["POST"])
    manager.APP.add_url_rule(f"{route_prefix}/register", "register", default_endpoints.register, methods=["POST"])
