from functools import wraps
from flask import jsonify, request

from silence.db import dal
from silence import sql as SQL
from silence.sql import get_sql_op
from silence.settings import settings
from silence.utils.min_type import Min
from silence.auth.tokens import check_token
from silence.logging.default_logger import logger
from silence.sql.converter import silence_to_mysql
from silence.sql.tables import get_primary_key
from silence.server import manager as server_manager
from silence.exceptions import HTTPError, TokenError

import re
import sys

OP_VERBS = {
    SQL.SELECT: 'get',
    SQL.INSERT: 'post',
    SQL.UPDATE: 'put',
    SQL.DELETE: 'delete',
}

RE_QUERY_PARAM = re.compile(r"^.*\$\w+/?$")

###############################################################################
# This is where the fun at v2
###############################################################################

def setup_endpoint(route, method, sql, auth_required=False, allowed_roles=["*"], description=None, request_body_params = []):
    logger.debug(f"Setting up endpoint {method} {route}")
    
    # if the query is requesting the logged user.
    logged_user= "$loggedId" in sql

    # Construct the API route taking the prefix into account
    route_prefix = settings.API_PREFIX
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]  # Drop the final /
    full_route = route_prefix + route

    # Warn if the pair SQL operation - HTTP verb is not the proper one
    check_method(sql, method, route)

    # Warn if the values of auth_required and allowed_roles don't make sense together
    check_auth_roles(auth_required, allowed_roles, method, route)

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

    # If it's a SELECT or a DELETE, make sure that all SQL params can be
    # obtained from the url AND the request body
    if sql_op in (SQL.INSERT, SQL.UPDATE):
        check_params_match(sql_params, url_params + request_body_params, route)

    # The handler function that will be passed to flask
    def route_handler(*args, **kwargs):
        # If this endpoint requires authentication, check that the
        # user has provided a session token and that it is valid
        if auth_required:
            userId = check_session(allowed_roles)
        
        # Collect all url pattern params
        request_url_params_dict = kwargs

        # If endpoint requires the logged userId it adds the pair (loggedId, loggedUserId)
        if logged_user:
            if not auth_required:
                userId = check_session(allowed_roles)
            if userId!=None:
                request_url_params_dict["loggedId"] = userId
        else:
                request_url_params_dict["loggedId"] = None

        # Convert the silence-style placeholders in the SQL query to proper MySQL placeholders
        query_string = silence_to_mysql(sql)

        # Default outputs
        res = None
        status = 200
        
        # SELECT/GET operations
        if sql_op == SQL.SELECT:
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
            #Construct a dict for all params expected in the request body, setting them to None if they have not been provided
            form = request.json if request.is_json else request.form
            body_params = {param: form.get(param, None) for param in request_body_params}

            # We have checked that sql_params is a subset of url_params U body_params,
            # construct a joint param object and use it to fill the SQL placeholders
            for param in url_params:
                body_params[param] = request_url_params_dict[param]

            if logged_user and auth_required:
                body_params["author"] = userId
            param_tuple = tuple(body_params[param] for param in sql_params)


            param_tuple = tuple(body_params[param] for param in sql_params)

            # Run the execute query
            res = dal.api_safe_update(query_string, param_tuple)

        return jsonify(res), status
    
    # flaskify_url() adapts the URL so that all $variables are converted to Flask-style <variables>
    server_manager.APP.add_url_rule(flaskify_url(full_route), method + route, route_handler, methods=[method])
    server_manager.API_SUMMARY.register_endpoint({"route": full_route, "method": method.upper(), "description": description})

###############################################################################
# Session token checker
def check_session(allowed_roles):
    token = request.headers.get("Token", default=None)
    if not token:
        raise HTTPError(401, "Unauthorized")

    try:
        user_data = check_token(token)
        u_data = settings.USER_AUTH_DATA['table'].lower()
        primary = get_primary_key(u_data)
        res = user_data[primary]
        return res
    except TokenError as exc:
        raise HTTPError(401, str(exc))

    # Check if the user's role is allowed to access this endpoint
    role_col_name = settings.USER_AUTH_DATA.get("role", None)
    if role_col_name:
        # Only check the role if we know the role column
        # Find the role of the user from the user data
        user_role = next((v for k, v in user_data.items() if k.lower() == role_col_name.lower()), None)
        if user_role not in allowed_roles and "*" not in allowed_roles:
            raise HTTPError(401, "Unauthorized")

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
        logger.error(f"The SQL query '{sql}' in the endpoint {endpoint} is not supported," +
                             " please use only SELECT/INSERT/UPDATE/DELETE.")
        sys.exit(1)

def check_auth_roles(auth_required, allowed_roles, method, route):
    # Raise an error if allowed_roles is not a list
    if not isinstance(allowed_roles, list):
        logger.error(f"The value '{allowed_roles}' for the allowed_roles parameter in " +
                            f"endpoint {method.upper()} {route} is not allowed, it must be a " +
                             "list of allowed roles.")
        sys.exit(1)

    # Warn if the user has specified some roles but auth_required is false,
    # since it will result in all users having access
    if not auth_required and len(allowed_roles) > 0 and allowed_roles != ["*"]:
        logger.warn(f"You have specified allowed roles in endpoint {method.upper()} {route}, " +
                     "but auth_required is False. This will result in all users having access " +
                     "regardless of their role.")

    # Warn if the user has specified an empty list of roles, and auth_required is true,
    # because it will result in noone having access
    if auth_required and len(allowed_roles) == 0:
        logger.warn(f"You have set auth_required to True in endpoint {method.upper()} {route}, " +
                     "but the list of allowed roles is empty. This will result in noone being able " +
                     "to access the endpoint.")

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
    if("loggedId" in diff):
        diff.remove("loggedId")

    if diff:
        params_str = ", ".join(f"${param}" for param in diff)
        logger.error(f"Error creating endpoint {route}: the parameters " +
                            f"{params_str} are expected by the SQL query but they are not provided in the URL " +
                            "or the request body.")
        sys.exit(1)