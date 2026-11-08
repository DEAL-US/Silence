from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

from silence.settings import settings

###############################################################################
# Passwords: argon2 hashes, or plain text if the project allows it
# (auth.password_mode = "plain"). Other hashes (pbkdf2, bcrypt...) are not
# supported: their passwords must be set again from the admin panel.
###############################################################################

_hasher = PasswordHasher()

def is_argon2(value):
    return isinstance(value, str) and value.startswith("$argon2")

def looks_like_hash(value):
    '''Whether a stored password looks like a hash of another algorithm'''
    if not isinstance(value, str):
        return False
    return value.startswith(("pbkdf2:", "scrypt:", "$2a$", "$2b$", "$2y$", "sha256$", "$pbkdf2", "$scrypt"))

def password_status(value):
    '''"argon2", "plain" or "unsupported" (another hash), as shown in the admin panel'''
    if is_argon2(value):
        return "argon2"
    if looks_like_hash(value):
        return "unsupported"
    return "plain"

def argon2_hash(password):
    '''The argon2 hash of a password (whatever the password mode of the project)'''
    return _hasher.hash(password)


def hash_password(password):
    '''The value to store for a password, according to the project's mode'''
    if settings.PASSWORD_MODE == "plain":
        return password
    return _hasher.hash(password)

def prepare_for_storage(value):
    '''Hashes a password that is about to be stored, unless it already is a hash'''
    if value is None or is_argon2(value):
        return value
    return hash_password(str(value))

class UnsupportedHash(Exception):
    pass

def verify_password(stored, given):
    '''Checks a password. Raises UnsupportedHash if the stored value cannot be checked'''
    if stored is None or given is None:
        return False
    if is_argon2(stored):
        try:
            return _hasher.verify(stored, given)
        except (VerifyMismatchError, VerificationError):
            return False
        except InvalidHashError:
            raise UnsupportedHash()
    if looks_like_hash(stored):
        raise UnsupportedHash()
    # A plain text password only works if the project allows them
    if settings.PASSWORD_MODE != "plain":
        raise UnsupportedHash()
    return stored == given
