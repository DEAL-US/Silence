from flask import request

from silence.auth.tokens import check_token
from silence.auth.users import users_pk
from silence.exceptions import HTTPError, TokenError
from silence.settings import settings

###############################################################################
# The logged user of a request: its token comes in the "Token" header.
###############################################################################

def get_logged_user(required=False):
    '''The user's data in the session token, or None. If required, a missing
    or invalid token is a 401'''
    token = request.headers.get("Token")
    if not token:
        if required:
            raise HTTPError(401, "You must be logged in to access this resource")
        return None
    try:
        return check_token(token)
    except TokenError as exc:
        if required:
            raise HTTPError(401, str(exc))
        return None


def get_field(row, name):
    '''Case-insensitive access to a column of a row'''
    if not row or not name:
        return None
    return next((v for k, v in row.items() if k.lower() == name.lower()), None)


def check_roles(user, allowed_roles):
    '''403 if the logged user's role is not one of the allowed ones ("*": any)'''
    if user is None:
        raise HTTPError(401, "You must be logged in to access this resource")
    if "*" in allowed_roles:
        return
    role = get_field(user, settings.USER_AUTH_DATA["role"])
    if role not in allowed_roles:
        raise HTTPError(403, "Your role does not allow you to access this resource")


def user_id_of(user):
    '''The primary key of the logged user (or None)'''
    if user is None:
        return None
    return get_field(user, users_pk())
