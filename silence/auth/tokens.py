from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous.exc import BadSignature, SignatureExpired

from silence.settings import settings
from silence.exceptions import TokenError

###############################################################################
# Token management: creation and checking
###############################################################################

auth = Serializer(settings.SECRET_KEY)

def create_token(data):
    return auth.dumps(data)

def check_token(token):
    try:
        auth.loads(token, max_age=settings.MAX_TOKEN_AGE)
    except SignatureExpired:
        raise TokenError("The session token has expired")
    except BadSignature:
        raise TokenError("The session token is not valid")
