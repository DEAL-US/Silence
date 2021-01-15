from functools import wraps
from flask import jsonify, request

from silence.auth.tokens import check_token
from silence.server import manager as server_manager
from silence.db import dal
from silence import sql as SQL
from silence.sql import get_sql_op
from silence.sql.converter import silence_to_mysql
from silence.settings import settings
from silence.exceptions import EndpointError, HTTPError, TokenError
from silence.logging.default_logger import logger
from silence.utils.min_type import Min

import inspect
import re

OP_VERBS = {
    SQL.SELECT: 'get',
    SQL.INSERT: 'post',
    SQL.UPDATE: 'put',
    SQL.DELETE: 'delete',
}

RE_QUERY_PARAM = re.compile(r"^.*\$\w+/?$")

###############################################################################
# This is where the fun at
###############################################################################

def endpoint(route, method, sql, auth_required=False, description=None):
    logger.debug(f"Setting up endpoint {method} {route}")

    # Construct the API route taking the prefix into account
    route_prefix = settings.API_PREFIX
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]  # Drop the final /
    full_route = route_prefix + route

    # Warn if the pair SQL operation - HTTP verb is not the proper one
    check_method(sql, method, route)

    # Extract the list of parameters that the user expects to receive
    # in the URL and in the SQL string
    sql_params = extract_params(sql)
    url_params = extract_params(route)

    # Get the required SQL operation
    sql_op = get_sql_op(sql)

    # If it's a SELECT or a DELETE, make sure that all SQL params can be
    # obtained from the url
    if sql_op in (SQL.SELECT, SQL.DELETE):
        check_params_match(sql_params, url_params, route)

    # wrapper is the inner decorator, so that the outer one can receive parameters
    def wrapper(func):
        @wraps(func)
        # The function itself that is being decorated (func)
        def decorator(*args, **kwargs):
            func(*args, **kwargs)

        # Get the list of arguments expected by the decorated function
        decorated_func_args = inspect.getargspec(func)[0]

        # If it's a SELECT or a DELETE, make sure that all SQL params can be
        # obtained from the url AND the request body
        if sql_op in (SQL.INSERT, SQL.UPDATE):
            check_params_match(sql_params, url_params + decorated_func_args, route)

        # The handler function that will be passed to flask
        def route_handler(*args, **kwargs):
            # If this endpoint requires authentication, check that the
            # user has provided a session token and that it is valid
            if auth_required:
                check_session()

            # Collect all url pattern params
            request_url_params_dict = kwargs

            # Convert the silence-style placeholders in the SQL query to proper MySQL placeholders
            query_string = silence_to_mysql(sql)

            # Default outputs
            res = None
            status = 200
            
            # SELECT/GET operations
            if sql_op == SQL.SELECT:
                # Call the decorated function, just in case (though it should do nothing)
                decorator()

                # The URL params have been checked to be enough to fill all SQL params
                url_pattern_params = tuple(request_url_params_dict[param] for param in sql_params)
                res = dal.api_safe_query(query_string, url_pattern_params)
                
                # Filter these results according to the URL query string, if there is one
                # Possible TO-DO: do this by directly editing the SQL query for extra efficiency
                res = filter_query_results(res, request.args)

                # In our teaching context, it is safe to assume that if the URL ends
                # with a parameter and we have no results, we should return a 404 code
                if RE_QUERY_PARAM.match(route) and not res:
                    raise HTTPError(404, "Not found")

            else:  # POST/PUT/DELETE operations
                # Construct a dict for all params expected in the request body,
                # setting them to None if they have not been provided
                form = request.json if request.is_json else request.form
                body_params = {param: form.get(param, None) for param in decorated_func_args}

                # Call the decorated function with these parameters to allow the
                # user to validate them
                decorator(**body_params)

                # We have checked that sql_params is a subset of url_params U body_params,
                # construct a joint param object and use it to fill the SQL placeholders
                for param in url_params:
                    body_params[param] = request_url_params_dict[param]

                param_tuple = tuple(body_params[param] for param in sql_params)

                # Run the execute query
                res = dal.api_safe_update(query_string, param_tuple)

            return jsonify(res), status
        
        # flaskify_url() adapts the URL so that all $variables are converted to Flask-style <variables>
        server_manager.APP.add_url_rule(flaskify_url(full_route), method + route, route_handler, methods=[method])
        server_manager.API_TREE.add_url(full_route)
        server_manager.API_TREE.register_endpoint({"route": full_route, "method": method.upper(), "description": description})

        return decorator
    return wrapper

###############################################################################
# Session token checker
def check_session():
    token = request.headers.get("Token", default=None)
    if not token:
        raise HTTPError(401, "Unauthorized")

    try:
        check_token(token)
    except TokenError as exc:
        raise HTTPError(401, str(exc))

###############################################################################
# Aux stuff for the handler function

# Implements filtering, ordering and paging using query strings
def filter_query_results(data, args):
    # Grab all parameters from the query string
    sort_param = args.get("_sort", None)
    sort_reverse = "_order" in args and args["_order"] == "desc"

    try:
        limit = int(args.get("_limit", None))
    except (ValueError, TypeError):
        limit = None

    try:
        page = int(args.get("_page", None))
    except (ValueError, TypeError):
        page = None

    # Filter, sort and paginate results
    filter_criteria = [pair for pair in args.items() if not pair[0][0] == "_"]
    filter_func = lambda elem: all(k not in elem or str(elem[k]).lower() == v.lower() for k, v in filter_criteria)
    res = list(filter(filter_func, data))

    def order_key_func(elem):
        v = elem[sort_param]
        return v if v is not None else Min  # Avoids comparisons against None

    try:
        res.sort(key=order_key_func, reverse=sort_reverse)
    except KeyError: pass

    offset = limit * page if limit and page else 0
    top = offset + limit if limit else len(res)
    return res[offset:top]

###############################################################################
# Aux stuff for checking and parsing

# Checks whether the SQL operation and the HTTP verb match
def check_method(sql, verb, endpoint):
    sql_op = get_sql_op(sql)

    if sql_op in OP_VERBS:
        correct_verb = OP_VERBS[sql_op]

        if correct_verb != verb.lower():
            # Warn the user about the correct verb to use
            logger.warn(
                f"The '{verb.upper()}' HTTP verb is not correct for the SQL {sql_op.upper()} " +
                f"operation in endpoint {verb.upper()} {endpoint}, the correct verb is {correct_verb.upper()}."
            )
    else:
        # What has the user put here?
        raise EndpointError(f"The SQL query '{sql}' in the endpoint {endpoint} is not supported," +
                             " please use only SELECT/INSERT/UPDATE/DELETE.")

# Returns a list of $params in a SQL query or endpoint route,
# without the $'s
def extract_params(string):
    res = re.findall(r"\$\w+", string)
    return [x[1:] for x in res]

# Convers $url_param to <url_param>
def flaskify_url(url):
    return re.sub(r"\$(\w+)", r"<\1>", url)

# Checks whether all SQL params can be filled with the provided params
def check_params_match(sql_params, user_params, route):
    sql_params_set = set(sql_params)
    user_params_set = set(user_params)
    diff = sql_params_set.difference(user_params_set)

    if diff:
        params_str = ", ".join(f"${param}" for param in diff)
        raise EndpointError(f"Error creating endpoint {route}: the parameters " +
                            f"{params_str} are expected by the SQL query but they are not provided in the URL " +
                            "or the request body.")