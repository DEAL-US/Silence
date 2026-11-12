import requests
from silence.logging.default_logger import logger
from utils import BASE_URL, get_token_for_user

# Owners and roles (owner_endpoints.json), with the data of populate_database.sql:
#   1 perianez (Manager, no boss), 2 jimenez (CEO, boss 1), 3 lacalle (Manager, boss 2),
#   4 linares (Programmer, boss 2), 5 alvarez (no role, boss 3)


def as_user(email):
    token = get_token_for_user(email)
    return {"Token": token} if token else {}


def try_owner_on_reads():
    # The collection: only the rows of the logged user
    r = requests.get(f"{BASE_URL}/employees/team", headers=as_user("jimenez@company.com"))
    assert r.status_code == 200
    assert sorted(e["employeeId"] for e in r.json()) == [3, 4]
    r = requests.get(f"{BASE_URL}/employees/team", headers=as_user("alvarez@company.com"))
    assert r.status_code == 200 and r.json() == []
    assert requests.get(f"{BASE_URL}/employees/team").status_code == 401
    # One row: its owner sees it; another user does not (404)
    assert requests.get(f"{BASE_URL}/employees/team/3", headers=as_user("jimenez@company.com")).status_code == 200
    assert requests.get(f"{BASE_URL}/employees/team/3", headers=as_user("linares@company.com")).status_code == 404


def try_owner_or_roles():
    route = f"{BASE_URL}/employees/team/5/salary"
    body = {"salary": 1300}  # Its current salary: the data do not change
    # The owner (the boss of 5 is 3), whatever its role
    assert requests.put(route, json=body, headers=as_user("lacalle@company.com")).status_code == 200
    # A role of the list (CEO), on a row that is not its own
    assert requests.put(route, json=body, headers=as_user("jimenez@company.com")).status_code == 200
    # Neither the owner nor a role of the list
    assert requests.put(route, json=body, headers=as_user("linares@company.com")).status_code == 403
    assert requests.put(route, json=body).status_code == 401


def try_roles_imply_session():
    assert requests.get(f"{BASE_URL}/departments/ceoOnly").status_code == 401
    assert requests.get(f"{BASE_URL}/departments/ceoOnly", headers=as_user("linares@company.com")).status_code == 403
    assert requests.get(f"{BASE_URL}/departments/ceoOnly", headers=as_user("jimenez@company.com")).status_code == 200


def run():
    print("Testing owners and roles...")
    logger.warning("testing owners and roles")
    try_owner_on_reads()
    try_owner_or_roles()
    try_roles_imply_session()
