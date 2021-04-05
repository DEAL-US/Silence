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

    for folder in ("api", "endpoints"):
        try:
            pyfiles = [f for f in listdir(folder) if f.endswith(".py")]
        except FileNotFoundError:
            continue

        if folder == "api" and pyfiles:
            logger.warning("Please rename the folder that contains your endpoints to 'endpoints/' instead of 'api/'")
            logger.warning("Support for the 'api/' folder will be dropped in the future.")

        for pyfile in pyfiles:
            module_name = folder + "." + splitext(pyfile)[0]
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

    if settings.ENABLE_SUMMARY:
        manager.API_SUMMARY.register_endpoint({
                "route": route_prefix,
                "method": "GET",
                "desc": "Returns the data regarding the API endpoints",
        })
        manager.APP.add_url_rule(route_prefix, "APItreeHELP", default_endpoints.show_api_endpoints, methods=["GET"])

    if settings.ENABLE_LOGIN:
        login_route = f"{route_prefix}/login"
        manager.API_SUMMARY.register_endpoint({
            "route": login_route,
            "method": "POST",
            "desc": "Starts a new session, returning a session token and the user data if the login is successful",
        })
        manager.APP.add_url_rule(login_route, "login", default_endpoints.login, methods=["POST"])

    if settings.ENABLE_REGISTER:
        register_route = f"{route_prefix}/register"
        manager.API_SUMMARY.register_endpoint({
            "route": register_route,
            "method": "POST",
            "desc": "Creates a new user, returning a session token and the user data if the register is successful",
        })
        manager.APP.add_url_rule(register_route, "register", default_endpoints.register, methods=["POST"])
