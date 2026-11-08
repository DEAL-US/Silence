import threading
import time

from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous.exc import BadSignature, SignatureExpired

from silence.settings import settings
from silence.exceptions import TokenError
from silence.logging.default_logger import logger
from silence.utils.silence_json_encoder import SilenceJSONSerializer

###############################################################################
# Token management: creation, checking and closing (logout).
# A token is the user's row (without the password) signed with the project's
# secret key: Silence keeps no session tables in the database. The tokens of
# the sessions closed with /logout are kept in memory until they expire (after
# restarting Silence, a closed session that has not expired is valid again).
###############################################################################

_revoked = {}  # Closed token -> when it expires
_lock = threading.Lock()


def _serializer():
    return Serializer(settings.SECRET_KEY, serializer=SilenceJSONSerializer)

def create_token(data):
    '''Creates and returns a new token containing the given user data'''
    token = _serializer().dumps(data)
    logger.debug("Created new token %s[...]%s", token[:6], token[-6:])
    return token

def check_token(token):
    '''Checks whether the provided token is valid. Returns the user's data
    contained inside the token if it is, otherwise raises a TokenError.'''
    logger.debug("Checking received token %s[...]%s", token[:6], token[-6:])
    with _lock:
        closed = token in _revoked
    if closed:
        raise TokenError("The session has been closed (logout)")
    try:
        return _serializer().loads(token, max_age=settings.MAX_TOKEN_AGE)
    except SignatureExpired:
        raise TokenError("The session token has expired")
    except BadSignature:
        raise TokenError("The session token is not valid")


def revoke_token(token):
    '''Closes a session: its token is no longer accepted. False if it is not valid'''
    try:
        check_token(token)
    except TokenError:
        return False
    now = time.time()
    with _lock:
        for t, expires in list(_revoked.items()):  # The expired ones are no longer needed
            if expires < now:
                del _revoked[t]
        _revoked[token] = now + settings.MAX_TOKEN_AGE
    return True
