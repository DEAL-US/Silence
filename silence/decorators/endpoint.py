from functools import wraps
from flask import jsonify

from silence.server import manager as server_manager
from silence.db.dal import query
from silence.settings import settings

###############################################################################
# This is where the fun at
###############################################################################

def endpoint(route, method, sql, auth_required=False):
    route_prefix = settings.API_PREFIX
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]  # Drop the final /

    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            func(*args, **kwargs)

        def route_handler():
            decorator()
            res = query(sql)
            return jsonify(res), 200
        
        server_manager.APP.add_url_rule(route_prefix + route, route, route_handler, methods=[method])

        return decorator
    return wrapper