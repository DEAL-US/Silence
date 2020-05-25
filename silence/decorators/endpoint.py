from functools import wraps
from flask import jsonify, request

from silence.server import manager as server_manager
from silence.db import dal
from silence import sql as SQL
from silence.sql import get_sql_op
from silence.sql.validator import sql_is_ok
from silence.sql.converter import silence_to_mysql
from silence.settings import settings
from silence.exceptions import SQLWarning, EndpointWarning, EndpointError, HTTPError

import warnings
import re

OP_VERBS = {
    SQL.SELECT: 'get',
    SQL.INSERT: 'post',
    SQL.UPDATE: 'put',
    SQL.DELETE: 'delete',
}

###############################################################################
# This is where the fun at
###############################################################################

def endpoint(route, method, sql, auth_required=False):
    # Construct the API route taking the prefix into account
    route_prefix = settings.API_PREFIX
    if route_prefix.endswith("/"):
        route_prefix = route_prefix[:-1]  # Drop the final /
    full_route = route_prefix + route

    # Warn if the SQL seems to not be correct
    check_sql(sql, route)

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

        # The handler function that will be passed to flask
        def route_handler(*args, **kwargs):
            # Collect all url pattern params
            request_params = kwargs

            # Convert the silence-style placeholders in the SQL query to proper MySQL placeholders
            query_string = silence_to_mysql(sql)

            # Default outputs
            res = None
            status = 200
            
            if sql_op == SQL.SELECT:
                # Call the decorated function, just in case (though it should do nothing)
                decorator()

                # The URL params have been checked to be enough to fill all SQL params
                query_params = tuple(request_params[param] for param in sql_params)
                res = dal.query(query_string, query_params)
                
                # Filter these results according to the URL query string, if there is one
                # Possible TO-DO: do this by directly editing the SQL query for extra efficiency
                res = filter_query_results(res, request.args)

                # In our teaching context, it is safe to assume that if there is
                # at least one URL parameter and we have no results,
                # we should return a 404 code
                if url_params and not res:
                    raise HTTPError("Not found", 404)
            else:
                # TO-DO: updates
                raise NotImplementedError

            return jsonify(res), status
        
        # flaskify adapts the URL so that all $variables are converted to Flask-style <variables>
        server_manager.APP.add_url_rule(flaskify_url(full_route), route, route_handler, methods=[method])

        return decorator
    return wrapper

###############################################################################
# Aux stuff for the handler function
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

    try:
        res.sort(key=lambda elem: elem[sort_param], reverse=sort_reverse)
    except KeyError: pass

    offset = limit * page if limit and page else 0
    top = offset + limit if limit else len(res)
    return res[offset:top]

###############################################################################
# Aux stuff for checking and parsing

# Checks whether an SQL string may contain errors
# This may not be super trustworthy, so we just raise a Warning instead
# of an exception.
def check_sql(sql, endpoint):
    if not sql_is_ok(sql):
        warnings.warn(f"The SQL string '{sql}' for the endpoint {endpoint} seems to contain errors.", SQLWarning)

# Checks whether the SQL operation and the HTTP verb match
def check_method(sql, verb, endpoint):
    sql_op = get_sql_op(sql)

    if sql_op in OP_VERBS:
        correct_verb = OP_VERBS[sql_op]

        if correct_verb != verb.lower():
            # Warn the user about the correct verb to use
            warnings.warn(
                f"The '{verb.upper()}' HTTP verb is not correct for the SQL {sql_op.upper()} " +
                f"operation in endpoint {endpoint}, the correct verb is {correct_verb.upper()}.",
                EndpointWarning
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

# Checks whether all SQL params can be filled with URL-pattern params
# This is done for GETs and DELETEs where no request body is sent
def check_params_match(sql_params, url_params, route):
    sql_params = set(sql_params)
    url_params = set(url_params)
    diff = sql_params.difference(url_params)

    if diff:
        params_str = ", ".join(f"${param}" for param in diff)
        raise EndpointError(f"Error creating endpoint {route}: the parameters " +
                            f"{params_str} are expected by the SQL query but they are not provided in the URL.")