from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous.exc import BadSignature, SignatureExpired

from silence.settings import settings
from silence.exceptions import TokenError
from silence.logging.default_logger import logger
from silence.utils.silence_json_encoder import SilenceJSONSerializer

###############################################################################
# Token management: creation and checking
###############################################################################

auth = Serializer(settings.SECRET_KEY, serializer=SilenceJSONSerializer)

def create_token(data):
    '''Creates and returns a new token containing the given user data'''
    token = auth.dumps(data)
    logger.debug("Created new token %s[...]%s", token[:6], token[-6:])
    return token

def check_token(token):
    '''Checks whether the provided token is valid. Returns the user's data
    contained inside the token if it is, otherwise raises a TokenError.'''
    logger.debug("Checking received token %s[...]%s", token[:6], token[-6:])
    try:
        user_data = auth.loads(token, max_age=settings.MAX_TOKEN_AGE)
        logger.debug("The token is correct")
        return user_data
    except SignatureExpired:
        logger.debug("The token has expired")
        raise TokenError("The session token has expired")
    except BadSignature:
        logger.debug("The token is not valid")
        raise TokenError("The session token is not valid")

    