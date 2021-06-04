import importlib
import json

from os import listdir, getcwd, path, mkdir
from os.path import splitext

from silence.sql.tables import get_tables, get_views, get_primary_key

from silence.server import manager, default_endpoints
from silence.server.endpoint import setup_endpoint
from silence.settings import settings
from silence.logging.default_logger import logger

###############################################################################
# Look for .json files inside the project's "/api" folder
# and generate the endpoints for them.
###############################################################################

def load_user_endpoints():
    logger.debug("Looking for custom endpoints...")

    # Load every .json file inside the endpoints/ or api/ folders
    curr_dir = getcwd()
    endpoints_dir_new = curr_dir + "\\endpoints"
    endpoints_dir_old = curr_dir + "\\api"

    if path.isdir(endpoints_dir_old):
        warnign_old_folder()
        endpoints_dir = endpoints_dir_old

        if path.isdir(endpoints_dir_new):
            endpoints_dir = endpoints_dir_new
            logger.warning("You appear to have both api/ and endpoints/ folders, the latter will be used.")
    
    elif path.isdir(endpoints_dir_new):
        endpoints_dir = endpoints_dir_new
    
    auto_dir = endpoints_dir + "\\default"

    endpoint_paths_json = [endpoints_dir + f"\\{f}" for f in listdir(endpoints_dir) if f.endswith('.json')]
    endpoint_paths_json += [auto_dir + f"\\{f}" for f in listdir(auto_dir) if f.endswith('.json')]

    for jsonfile in endpoint_paths_json:
        with open(jsonfile, "r") as ep:
            mid = json.load(ep)
            endpoints = list(mid.values())
            for endpoint in endpoints:

                kwargs_nones = dict(auth_required = endpoint.get('auth_required'), allowed_roles = endpoint.get('allowed_roles'), 
                description = endpoint.get('description'), request_body_params = endpoint.get('request_body_params'))

                kwargs = {k: v for k, v in kwargs_nones.items() if v is not None}

                setup_endpoint(endpoint['route'], endpoint['method'], endpoint['sql'], **kwargs)

    # SUPPORT FOR .PY FILES:
    pyfiles = [f for f in listdir(endpoints_dir) if f.endswith('.py')]
    mod_aux = endpoints_dir.split("\\")
    folder = mod_aux[len(mod_aux)-1].strip()
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


###############################################################################
# Get the entities from the database and create CRUD endpoint files (json) for them
###############################################################################
def create_entity_endpoints():
    # Folder handling

    curr_dir = getcwd()
    endpoints_dir_new = curr_dir + "\\endpoints"
    endpoints_dir_old = curr_dir + "\\api"

    if path.isdir(endpoints_dir_old):
        warnign_old_folder()
        endpoints_dir = endpoints_dir_old

        if path.isdir(endpoints_dir_new):
            endpoints_dir = endpoints_dir_new
            logger.warning("You appear to have both api/ and endpoints/ folders, the latter will be used.")
    
    elif path.isdir(endpoints_dir_new):
        endpoints_dir = endpoints_dir_new
    
    auto_dir = endpoints_dir + "\\default"

    logger.debug(f"selected endpoint directory -->  {auto_dir}")

    if not path.isdir(auto_dir):
        logger.debug(f"creating directory -->  {auto_dir}")
        mkdir(auto_dir)
    
    # Endpoint files creation
    tables = get_tables()
    
    for table in list(tables.items()):
        logger.debug(f"generating endpoints for {table[0]}")
        pk = get_primary_key(table[0])[0]['Column_name']
        endpoints = {}
        table[1].remove(pk)

        endpoints["get_all"] = generate_get_all(table)
        endpoints["get_by_id"] = generate_get_by_id(table, pk)
        endpoints["add"] = generate_create(table, pk)
        endpoints["update"] = generate_update(table,pk)
        endpoints["delete"] = generate_delete(table,pk)

        dicts_to_file(endpoints, table[0], auto_dir)
    
    views = get_views()

    for view in list(views.items()):
        logger.debug(f"generating endpoints for {view[0]}")
        endpoints = {}

        endpoints["get_all"] = generate_get_all(view)
        dicts_to_file(endpoints, view[0], auto_dir)



def dicts_to_file(dicts, name, auto_dir):
    all_jsons = "{\n"
    for d in list(dicts.items()):
        all_jsons += "\""+str(d[0]) +"\":" +json.dumps(d[1]) + ",\n"
    
    all_jsons = all_jsons[:-2]
    all_jsons += " \n}"
    with open(auto_dir+f"\\{name}.json", "w") as endpoint:
        endpoint.write(all_jsons)

def generate_get_all(table):
    res = {}
    name = table[0]
    res["route"] = f"/{name}"
    res["method"] = "GET"
    res["sql"] = f"SELECT * FROM {name}"
    # res["auth_required"] = False
    # res["allowed_roles"] = ["*"]
    res["description"] = f"Gets all {name}s"
    # res["request_body_params"] = []
    return res

def generate_get_by_id(table, pk):
    res = {}
    name = table[0]
    res["route"] = f"/{name}/${pk}"
    res["method"] = "GET"
    res["sql"] = f"SELECT * FROM {name} WHERE {pk} = ${pk}"
    # res["auth_required"] = False
    # res["allowed_roles"] = ["*"]
    res["description"] = f"Gets a {name} with corresponding primary key"
    # res["request_body_params"] = []
    return res

def generate_create(table, pk):
    res = {}
    name = table[0]
    param_list = table[1]

    res["route"] = f"/{name}"
    res["method"] = "POST"
    res["sql"] = f"INSERT INTO {name}" + params_to_string(param_list, "", is_create=True) + " VALUES " + params_to_string(param_list, "$", is_create=True)
    # res["auth_required"] = False
    # res["allowed_roles"] = ["*"]
    res["description"] = f"creates a new {name}"
    res["request_body_params"] = param_list
    return res

def generate_update(table, pk):
    res = {}
    name = table[0]
    param_list = table[1]

    res["route"] = f"/{name}/${pk}"
    res["method"] = "PUT"
    res["sql"] = f"UPDATE {name} SET " + params_to_string(param_list, "", is_update=True) + f" WHERE {pk} = ${pk}"
    # res["auth_required"] = False
    # res["allowed_roles"] = ["*"]
    res["description"] = f"updates an existing {name} with corresponding primary key"
    res["request_body_params"] = param_list
    return res

def generate_delete(table,pk):
    res = {}
    name = table[0]
    res["route"] = f"/{name}/${pk}"
    res["method"] = "DELETE"
    res["sql"] = f"DELETE FROM {name} WHERE {pk} = ${pk}"
    # res["auth_required"] = False
    # res["allowed_roles"] = ["*"]
    res["description"] = f"deletes an existing {name} with corresponding primaery key"
    # res["request_body_params"] = []
    return res

def params_to_string(param_list, char_add, is_create = False, is_update = False):
    if is_create:
        res = "("
        for p in param_list:
            res += char_add + p +", "
        res = res[:-2]
        res += ")"
        return res

    if is_update:
        res = ""
        for p in param_list:
            res +=  p +" = $"+ p + ", "
        res = res[:-2]
        return res

def warnign_old_folder():
    logger.warning("Please rename the folder that contains your endpoints to 'endpoints/' instead of 'api/'")
    logger.warning("Support for the 'api/' folder will be dropped in the future.")