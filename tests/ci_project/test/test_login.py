import requests
from silence.logging.default_logger import logger


from utils import BASE_URL

def try_login_empty():
    data = {}
    r = requests.post(BASE_URL + "/login", json=data)
    assert r.status_code == 400
    assert "sessionToken" not in r.json()

def try_login_no_password():
    data = {
        "email": "perianez@company.com",
    }
    r = requests.post(BASE_URL + "/login", json=data)
    assert r.status_code == 400
    assert "sessionToken" not in r.json()

def try_login_no_id():
    data = {
        "password": "perianez",
    }
    r = requests.post(BASE_URL + "/login", json=data)
    assert r.status_code == 400
    assert "sessionToken" not in r.json()

def try_login_incorrect_email():
    data = {
        "email": "notexists@null.com",
        "password": "perianez",
    }
    r = requests.post(BASE_URL + "/login", json=data)
    assert r.status_code == 400
    assert "sessionToken" not in r.json()

def try_login_incorrect_password():
    data = {
        "email": "perianez@company.com",
        "password": "djgnhasfkjghnahslfkjfgjkl",
    }
    r = requests.post(BASE_URL + "/login", json=data)
    assert r.status_code == 400
    assert "sessionToken" not in r.json()

def try_login_ok():
    data = {
        "email": "perianez@company.com",
        "password": "perianez",
    }
    r = requests.post(BASE_URL + "/login", json=data)
    assert r.status_code == 200
    assert "sessionToken" in r.json()

def try_logout():
    token = requests.post(BASE_URL + "/login", json={"email": "perianez@company.com", "password": "perianez"}).json()["sessionToken"]
    headers = {"Token": token}
    assert requests.get(BASE_URL + "/employees/logged", headers=headers).status_code == 200
    assert requests.post(BASE_URL + "/logout", headers=headers).status_code == 200
    # The closed session is no longer accepted, nor closed twice
    r = requests.get(BASE_URL + "/employees/logged", headers=headers)
    assert r.status_code == 401 and "logout" in r.json()["message"]
    assert requests.post(BASE_URL + "/logout", headers=headers).status_code == 401
    assert requests.post(BASE_URL + "/logout").status_code == 401
    # There is no register: the users are created with the endpoints of their table
    assert requests.post(BASE_URL + "/register", json={"email": "x@x.com", "password": "x"}).status_code in (404, 405)

def run():
    print("Testing /login...")
    
    logger.warning("testing login empty fields")
    try_login_empty()
    
    logger.warning("testing login empty password")
    try_login_no_password()
    
    logger.warning("testing login empty user")
    try_login_no_id()
    
    logger.warning("testing login incorrect user")
    try_login_incorrect_email()
    
    logger.warning("testing login incorrect password")
    try_login_incorrect_password()
    
    logger.warning("testing login success")
    try_login_ok()

    logger.warning("testing logout")
    try_logout()
