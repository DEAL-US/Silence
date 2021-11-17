import json

from os import listdir, getcwd, path, mkdir
from flask import jsonify

from silence.server import manager as server_manager
from silence.server import endpoint as server_endpoint

from silence.settings import settings
from silence.logging.default_logger import logger


# SILENCE RUN OPERATIONS

###############################################################################
# Look for .json files inside the project's "/endpoints" folder
# and generate the endpoints for them.
###############################################################################
def load_user_endpoints():
    logger.debug("Looking for custom endpoints...")

    # Load every .json file inside the endpoints/ or api/ folders
    curr_dir = getcwd()
    endpoints_dir = curr_dir + "/endpoints"

    if not path.isdir(endpoints_dir):
        mkdir(endpoints_dir)
    
    auto_dir = endpoints_dir + "/auto"

    endpoint_paths_json_user = [endpoints_dir + f"/{f}" for f in listdir(endpoints_dir) if f.endswith('.json')]

    if path.isdir(auto_dir):
        endpoint_paths_json_default = [auto_dir + f"/{f}" for f in listdir(auto_dir) if f.endswith('.json')]
        endpoint_paths_json = endpoint_paths_json_user + endpoint_paths_json_default
    else:
        endpoint_paths_json = endpoint_paths_json_user

    for jsonfile in endpoint_paths_json:
        with open(jsonfile, "r") as ep:
            endpoints = list(json.load(ep).values())

            for endpoint in endpoints:
                kwargs_nones = dict(auth_required = endpoint.get('auth_required'), allowed_roles = endpoint.get('allowed_roles'), 
                description = endpoint.get('description'), request_body_params = endpoint.get('request_body_params'))

                kwargs = {k: v for k, v in kwargs_nones.items() if v is not None}

                server_endpoint.setup_endpoint(endpoint['route'], endpoint['method'], endpoint['sql'], **kwargs)

###############################################################################
# Register the Silence-provided endpoints
###############################################################################
def load_default_endpoints():
    from silence.server import default_endpoints
    route_prefix = settings.API_PREFIX
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]

    if settings.ENABLE_SUMMARY:
        server_manager.API_SUMMARY.register_endpoint({
                "route": route_prefix,
                "method": "GET",
                "desc": "Returns the data regarding the API endpoints",
        })
        server_manager.APP.add_url_rule(route_prefix, "APItreeHELP", show_api_endpoints, methods=["GET"])

    if settings.ENABLE_LOGIN:
        login_route = f"{route_prefix}/login"
        server_manager.API_SUMMARY.register_endpoint({
            "route": login_route,
            "method": "POST",
            "desc": "Starts a new session, returning a session token and the user data if the login is successful",
        })
        server_manager.APP.add_url_rule(login_route, "login", default_endpoints.login, methods=["POST"])

    if settings.ENABLE_REGISTER:
        register_route = f"{route_prefix}/register"
        server_manager.API_SUMMARY.register_endpoint({
            "route": register_route,
            "method": "POST",
            "desc": "Creates a new user, returning a session token and the user data if the register is successful",
        })
        server_manager.APP.add_url_rule(register_route, "register", default_endpoints.register, methods=["POST"])


def show_api_endpoints():
    return jsonify(server_manager.API_SUMMARY.get_endpoint_list()), 200