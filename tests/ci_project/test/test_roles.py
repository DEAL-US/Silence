import requests
from silence.logging.default_logger import logger
from test_employees import get_all as get_employees
from utils import get_token_for_user

from utils import BASE_URL

def try_endpoint_with_user(route, email, expected_access):
    token = get_token_for_user(email)
    headers = {"Token": token} if token else {}

    r = requests.get(f"{BASE_URL}/{route}", headers=headers)
    # Silence 3: 401 without a session, 403 with a role that is not allowed
    expected_code = 200 if expected_access else (401 if email is None else 403)

    try:
        assert int(r.status_code) == int(expected_code)
    except AssertionError:
        logger.error(f"The employee {email} got status code {r.status_code} when expecting {expected_code}")
        raise

###############################################################################

def try_free_access():
    route = "departments/freeAccess"
    try_endpoint_with_user(route, None, expected_access=True)
    
    for emp in get_employees():
        try_endpoint_with_user(route, emp["email"], expected_access=True)

def try_only_logged():
    route = "departments/onlyLogged"
    try_endpoint_with_user(route, None, expected_access=False)
    
    for emp in get_employees():
        try_endpoint_with_user(route, emp["email"], expected_access=True)

def try_only_manager_or_ceo():
    route = "departments/onlyManagerOrCEO"
    try_endpoint_with_user(route, None, expected_access=False)
    
    for emp in get_employees():
        can_access = emp["position"] in ("Manager", "CEO")
        try_endpoint_with_user(route, emp["email"], expected_access=can_access)

def try_only_ceo():
    route = "departments/onlyCEO"
    try_endpoint_with_user(route, None, expected_access=False)
    
    for emp in get_employees():
        can_access = emp["position"] == "CEO"
        try_endpoint_with_user(route, emp["email"], expected_access=can_access)

def run():
    print("Testing role restrictions...")

    logger.warning("Testing free access")
    try_free_access()
    
    logger.warning("Testing only logged")
    try_only_logged()

    logger.warning("Testing only Manager or CEO")
    try_only_manager_or_ceo()

    logger.warning("Testing only CEO")
    try_only_ceo()