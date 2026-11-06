import requests
from silence.logging.default_logger import logger
from test_employees import get_all as get_employees
from utils import get_token_for_user

from utils import BASE_URL

def try_endpoint_with_user(route, email, expected_access):
    password = email.split("@")[0]
    r = requests.post(f"{BASE_URL}/{route}", data={"email":email, "password":password})

    expected_code = 200 if expected_access else 401

    try:
        assert int(r.status_code) == int(expected_code)
    except AssertionError:
        logger.error(f"The employee {email} got status code {r.status_code} when expecting {expected_code}")
        raise

###############################################################################
def try_loggin_allowed_user():
    route = "login"
    try_endpoint_with_user(route, "perianez@company.com", expected_access=True)

def try_loggin_banned_user():
    route = "login"
    r = requests.put(f"{BASE_URL}/employees/ban/1")

    try_endpoint_with_user(route, "perianez@company.com", expected_access=False)

def try_loggin_unbanned_user():
    route = "login"
    r = requests.put(f"{BASE_URL}/employees/unban/1")

    try_endpoint_with_user(route, "perianez@company.com", expected_access=True)

def run():
    print("Testing banned capabilities restrictions...")

    logger.warning("Testing login with allowed user.")
    try_loggin_allowed_user()

    logger.warning("Testing login with banned user.")
    try_loggin_banned_user()
    
    logger.warning("Testing login with unbanned user.")
    try_loggin_unbanned_user()