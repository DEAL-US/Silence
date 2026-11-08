from silence.auth.passwords import verify_password, hash_password, UnsupportedHash
from silence.auth.tokens import create_token
from silence.db import dal
from silence.db.errors import to_http_error
from silence.db.schema import get_schema
from silence.exceptions import HTTPError, DatabaseError
from silence.settings import settings
from silence.logging.default_logger import logger
from silence.server.endpoints import request_body
from silence.server.session import get_field
from silence.auth import users as users_table

###############################################################################
# The endpoints provided by Silence: /login and /register, on the users table
# linked in the admin panel (the identifier may be in a referenced table: see
# silence/auth/users.py).
###############################################################################

def auth_fields():
    '''The users table and its fields (the identifier, by its name in the rows of the users)'''
    a = settings.USER_AUTH_DATA
    return a["table"], users_table.identifier_field(), a["password"], a["role"], a["active_status"]


def users_relation():
    rel = get_schema().get(settings.USER_AUTH_DATA["table"])
    if rel is None:
        raise HTTPError(500, f"The users table '{settings.USER_AUTH_DATA['table']}' does not exist")
    return rel


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


def register():
    table, id_field, pwd_field, role_field, active_field = auth_fields()
    rel = users_relation()
    form = request_body()
    identifier = form.get(id_field)
    password = form.get(pwd_field)

    if not identifier or not password:
        raise HTTPError(400, f"Both '{id_field}' and '{pwd_field}' are required")
    if users_table.identifier_is_external():
        raise HTTPError(409, f"The register is not available: the identifier ({settings.USER_AUTH_DATA['identifier']}) "
                             f"is not in the users table ({table}), so a new user needs a row there first")

    # Only the columns of the users table, with their real names. The role and whether the user is
    # active never come from the request (anybody could register as an administrator): the role is
    # auth.default_role (none if it is empty) and the new user is active
    role_col = rel.column(role_field).name if role_field else None
    active_col = rel.column(active_field).name if active_field else None
    user = {}
    for key, value in form.items():
        col = rel.column(key)
        if col is not None and not col.auto_increment and col.name not in (role_col, active_col):
            user[col.name] = value
    user[rel.column(pwd_field).name] = hash_password(password)
    if role_col:
        user[role_col] = settings.DEFAULT_ROLE_REGISTER
    if active_col:
        user[active_col] = settings.DEFAULT_ACTIVE_STATUS

    try:
        if find_user(identifier) is not None:
            raise HTTPError(400, f"There already exists another user with that {id_field}")
        cols = ", ".join(user)
        marks = ", ".join(["%s"] * len(user))
        dal.update(f"INSERT INTO {table}({cols}) VALUES ({marks})", tuple(user.values()))
        created = find_user(identifier)
    except DatabaseError as exc:
        raise to_http_error(exc, "register")

    return session_for(created), 200
