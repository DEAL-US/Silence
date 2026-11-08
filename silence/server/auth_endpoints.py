from flask import request

from silence.auth.passwords import verify_password, UnsupportedHash
from silence.auth.tokens import create_token, revoke_token
from silence.db import dal
from silence.db.errors import to_http_error
from silence.exceptions import HTTPError, DatabaseError
from silence.settings import settings
from silence.logging.default_logger import logger
from silence.server.endpoints import request_body
from silence.server.session import get_field
from silence.auth import users as users_table

###############################################################################
# The endpoints provided by Silence: /login and /logout, on the users table
# linked in the admin panel (the identifier may be in a referenced table: see
# silence/auth/users.py). There is no register: the users are rows of the
# database, created, changed and deleted with the endpoints of their table.
###############################################################################

def auth_fields():
    '''The users table and its fields (the identifier, by its name in the rows of the users)'''
    a = settings.USER_AUTH_DATA
    return a["table"], users_table.identifier_field(), a["password"], a["role"], a["active_status"]


def find_user(identifier):
    try:
        sql = f"{users_table.users_select()} WHERE {users_table.identifier_sql()} = %s"
    except users_table.UsersTableError as exc:
        raise HTTPError(500, f"The users table is not well linked: {exc}")
    rows = dal.query(sql, (identifier,))
    return rows[0] if rows else None


def public_user(user):
    '''The user's row without the password'''
    pwd = settings.USER_AUTH_DATA["password"].lower()
    return {k: v for k, v in user.items() if k.lower() != pwd}


def session_for(user):
    data = public_user(user)
    return {"sessionToken": create_token(data), "user": data}


def login():
    table, id_field, pwd_field, role_field, active_field = auth_fields()
    form = request_body()
    identifier = form.get(id_field)
    password = form.get(pwd_field)

    if not identifier or not password:
        raise HTTPError(400, f"Both '{id_field}' and '{pwd_field}' are required")

    try:
        user = find_user(identifier)
    except DatabaseError as exc:
        raise to_http_error(exc, "login")

    if user is None:
        raise HTTPError(400, "The user or the password are not correct")

    try:
        ok = verify_password(get_field(user, pwd_field), password)
    except UnsupportedHash:
        mode = "an argon2 hash" if settings.PASSWORD_MODE == "argon2" else "an argon2 hash or plain text"
        raise HTTPError(400, f"The stored password of this user is not {mode}: "
                             "set it again in the admin panel (Users)")
    if not ok:
        raise HTTPError(400, "The user or the password are not correct")

    if active_field and settings.CHECK_USER_IS_ACTIVE and not get_field(user, active_field):
        raise HTTPError(401, "This user has been deactivated")

    logger.debug("Login OK for %s", identifier)
    return session_for(user), 200


def logout():
    '''Closes the session of the request's token: it is no longer accepted'''
    token = request.headers.get("Token")
    if not token:
        raise HTTPError(401, "There is no session to close: send its token in the Token header")
    if not revoke_token(token):
        raise HTTPError(401, "The session token is not valid or has expired")
    return {"message": "Logged out"}, 200
