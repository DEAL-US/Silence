from flask import jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from silence.auth.tokens import create_token, check_token
from silence.db import dal
from silence.sql.builder import get_login_query, get_register_user_query
from silence.settings import settings
from silence.exceptions import HTTPError

###############################################################################
# Defines the default endpoints provided by Silence,
# mainly /login and /register
###############################################################################

USERS_TABLE = settings.USER_AUTH_DATA["table"]
IDENTIFIER_FIELD = settings.USER_AUTH_DATA["identifier"]
PASSWORD_FIELD = settings.USER_AUTH_DATA["password"]

def login():
    # Ensure that the user has sent the required fields
    username = request.form.get(IDENTIFIER_FIELD, default=None)
    password = request.form.get(PASSWORD_FIELD, default=None)

    if not username or not password:
        raise HTTPError(400, f"Both '{IDENTIFIER_FIELD}' and '{PASSWORD_FIELD}' are required")

    # Look if there is an user with such username
    q = get_login_query(USERS_TABLE, IDENTIFIER_FIELD, username)
    users = dal.api_safe_query(q)

    if not users:
        raise HTTPError(400, "User not found")

    # The identifier field should be unique (/register also takes care of that)
    # so we can just extract the first one
    user = users[0]
    
    # Check if the user's password matches the provided one
    if PASSWORD_FIELD not in user:
        raise HTTPError(500, f"The user has no attribute '{PASSWORD_FIELD}'")

    password_ok = check_password_hash(user[PASSWORD_FIELD], password)
    if not password_ok:
        raise HTTPError(400, "The password is not correct")

    # If we've reached here the login is successful, generate a session token
    # and return it with the logged user's info
    token = create_token(user)
    del user[PASSWORD_FIELD]
    res = {"sessionToken": token, "user": user}
    return jsonify(res), 200

def register():
    # Ensure that the user has sent the required fields
    username = request.form.get(IDENTIFIER_FIELD, default=None)
    password = request.form.get(PASSWORD_FIELD, default=None)

    # Ensure that the identifier is unique
    login_q = get_login_query(USERS_TABLE, IDENTIFIER_FIELD, username)
    other_users = dal.api_safe_query(login_q)

    if other_users:
        raise HTTPError(400, f"There already exists another user with that {IDENTIFIER_FIELD}")

    # Create the user object, replacing the password with the hashed one
    user = dict(request.form)
    user[PASSWORD_FIELD] = generate_password_hash(password)

    # Try to insert it in the DB
    # Since the /register endpoint must adapt to any possible table,
    # we assume that the user knows what they're doing and submits the
    # appropriate fields. Otherwise, the DB will just complain.
    register_q = get_register_user_query(USERS_TABLE, user)
    dal.api_safe_update(register_q)

    # Fetch the newly created user from the DB (some fields may have been)
    # automatically generated, like its ID
    # It should now exist
    user = dal.api_safe_query(login_q)[0]

    # If we've reached here the register is successful, generate a session token
    # and return it with the logged user's info
    token = create_token(user)
    del user[PASSWORD_FIELD]
    res = {"sessionToken": token, "user": user}
    return jsonify(res), 200
