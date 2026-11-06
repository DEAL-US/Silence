import requests
from silence.logging.default_logger import logger
from test_employees import get_all as get_employees
from utils import get_token_for_user

from utils import BASE_URL

def try_with_employee(route, emp):
    token = get_token_for_user(emp["email"])
    headers = {"Token": token}
    r = requests.get(f"{BASE_URL}/{route}", headers=headers)
    assert r.status_code == 200

    emp_response = r.json()[0]

    for field, value in emp_response.items():
        assert emp[field] == value

def try_normal():
    route = "employees/logged"
    for emp in get_employees():
        try_with_employee(route, emp)

def try_with_restriction():
    route = "employees/logged_restricted"
    r = requests.get(f"{BASE_URL}/{route}")
    assert r.status_code == 401

    for emp in get_employees():
        if emp["position"] == "CEO":
            try_with_employee(route, emp)


def run():
    print("Testing $loggedId...")
    
    logger.warning("Testing free access")
    try_normal()

    logger.warning("Testing with role restriction")
    try_with_restriction()