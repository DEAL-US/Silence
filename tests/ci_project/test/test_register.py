import requests
from silence.logging.default_logger import logger


from utils import BASE_URL

def get_all_employees():
    return requests.get(BASE_URL + "/employees").json()

def try_register_no_user():
    data = {
        "password": "123456",
        "departmentId": None,
        "bossId": 1,
        "firstName": "Pepito",
        "lastName": "Pruebas",
        "salary": 1337.00,
        # Never taken from the request: the role is auth.default_role (none here) and it is active
        "position": "Boss",
        "isActive": 0,
    }
    emps_before = get_all_employees()
    r = requests.post(BASE_URL + "/register", json=data)
    assert r.status_code == 400
    emps_after = get_all_employees()
    assert emps_after == emps_before

def try_register_no_password():
    data = {
        "email": "pepito@company.com",
        "departmentId": None,
        "bossId": 1,
        "firstName": "Pepito",
        "lastName": "Pruebas",
        "salary": 1337.00,
        # Never taken from the request: the role is auth.default_role (none here) and it is active
        "position": "Boss",
        "isActive": 0,
    }
    emps_before = get_all_employees()
    r = requests.post(BASE_URL + "/register", json=data)
    assert r.status_code == 400
    emps_after = get_all_employees()
    assert emps_after == emps_before

def try_register_repeated_email():
    emps_before = get_all_employees()
    data = {
        "email": emps_before[0]["email"],
        "password": "123456",
        "departmentId": None,
        "bossId": 1,
        "firstName": "Pepito",
        "lastName": "Pruebas",
        "salary": 1337.00,
    }
    r = requests.post(BASE_URL + "/register", json=data)
    assert r.status_code == 400
    emps_after = get_all_employees()
    assert emps_after == emps_before

def try_register_ok():
    data = {
        "email": "pruebas@company.com",
        "password": "pruebas",
        "departmentId": None,
        "bossId": 1,
        "firstName": "Pepito",
        "lastName": "Pruebas",
        "salary": 1337.00,
        # Never taken from the request: the role is auth.default_role (none here) and it is active
        "position": "Boss",
        "isActive": 0,
    }
    emps_before = get_all_employees()
    r = requests.post(BASE_URL + "/register", json=data)
    assert r.status_code == 200
    resp_data = r.json()

    emps_after = get_all_employees()
    assert len(emps_after) == len(emps_before) + 1

    assert "sessionToken" in resp_data
    assert "user" in resp_data

    resp_user = resp_data["user"]
    for k in data:
        if k not in ("password", "position", "isActive"):
            assert data[k] == resp_user[k]
    assert resp_user["position"] is None and resp_user["isActive"]

def try_register_repeated():
    data = {
        "email": "pruebas@company.com",
        "password": "pruebas",
        "departmentId": None,
        "bossId": 1,
        "firstName": "Pepito",
        "lastName": "Pruebas",
        "salary": 1337.00,
    }
    r = requests.post(BASE_URL + "/register", json=data)
    assert r.status_code == 400

def run():
    print("Testing /register...")
    logger.warning("testing register no user")
    try_register_no_user()
    
    logger.warning("testing register no password")
    try_register_no_password()
    
    logger.warning("testing register non unique email")
    try_register_repeated_email()
    
    logger.warning("testing register success")
    try_register_ok()
    
    logger.warning("testing register existing")
    try_register_repeated()