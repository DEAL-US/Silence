import requests
from silence.logging.default_logger import logger

from utils import BASE_URL, get_token, Min

def get_all():
    r = requests.get(BASE_URL + "/employees")
    assert r.status_code == 200
    return r.json()

###############################################################################

def try_get_from_view_topemployees():
    r = requests.get(f"{BASE_URL}/topemployees")
    assert r.status_code == 200
    top_emps = r.json()
    assert all(emp["salary"] > 2000 for emp in top_emps)

def try_get_all_sorted():
    emps = get_all()
    for attr in emps[0]:
        for order in ("asc", "desc"):
            r = requests.get(f"{BASE_URL}/employees?_sort={attr}&_order={order}")
            assert r.status_code == 200
            sorted_api = r.json()
            for e1, e2 in zip(sorted_api, sorted_api[1:]):
                attr1, attr2 = e1[attr], e2[attr]
                if attr1 is None: attr1 = Min
                if attr2 is None: attr2 = Min

                if order == "asc":
                    assert attr1 <= attr2
                else:
                    assert attr1 >= attr2

def try_get_all_filtered():
    filtered_pairs = []

    emps = get_all()
    for emp in emps:
        for attr in emp:
            val = emp[attr]
            pair = (attr, val)
            if pair in filtered_pairs: continue
            filtered_pairs.append(pair)

            r = requests.get(f"{BASE_URL}/employees?{attr}={val}")
            assert r.status_code == 200
            filtered_emps = list(filter(lambda x: x[attr] == val, emps))
            api_res = r.json()
            assert len(filtered_emps) == len(api_res)
            assert all(x in api_res for x in filtered_emps)

def try_get_all_paginated():
    emps = get_all()
    n_emps = len(emps)

    for limit in range(1, n_emps + 1):
        page = 0
        while limit * page < n_emps:
            r = requests.get(f"{BASE_URL}/employees?_limit={limit}&_page={page}")
            assert r.status_code == 200
            api_res = r.json()
            paginated = emps[limit * page:limit * (page + 1)]
            assert len(api_res) == len(paginated)
            assert all(x in api_res for x in paginated)
            page += 1

def try_get_one_ok():
    emps = get_all()

    for emp in emps:
        emp_id = emp["employeeId"]
        r = requests.get(f"{BASE_URL}/employees/{emp_id}")
        assert r.status_code == 200
        resp = r.json()
        assert len(resp) == 1
        assert r.json()[0] == emp

def try_get_one_not_exists():
    r = requests.get(f"{BASE_URL}/employees/2522461635631")
    assert r.status_code == 404

def try_create_unauthorized():
    emps_before = get_all()
    data = {
        "email": "testing_employee@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }

    r = requests.post(f"{BASE_URL}/employees", data=data)
    emps_after = get_all()
    assert r.status_code == 401
    assert emps_before == emps_after


def try_create_repeated_email():
    emps_before = get_all()
    email = emps_before[0]["email"]
    data = {
        "email": email,
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }

    headers = {"Token": get_token()}

    r = requests.post(f"{BASE_URL}/employees", data=data, headers=headers)
    emps_after = get_all()
    assert r.status_code == 400
    assert emps_before == emps_after

def try_create_no_password():
    emps_before = get_all()

    data = {
        "email": "testing_employee@company.com",
        "password": None,
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }

    headers = {"Token": get_token()}

    r = requests.post(f"{BASE_URL}/employees", data=data, headers=headers)
    emps_after = get_all()
    assert r.status_code == 400
    assert emps_before == emps_after

def try_create_no_name():
    emps_before = get_all()

    data = {
        "email": "testing_employee@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }

    headers = {"Token": get_token()}

    r = requests.post(f"{BASE_URL}/employees", data=data, headers=headers)
    emps_after = get_all()
    assert r.status_code == 400
    assert emps_before == emps_after

def try_create_invalid_salary():
    emps_before = get_all()

    data = {
        "email": "testing_employee@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": -420,
        "isActive": 1,
    }

    headers = {"Token": get_token()}

    r = requests.post(f"{BASE_URL}/employees", data=data, headers=headers)
    emps_after = get_all()
    assert r.status_code == 400
    assert emps_before == emps_after

def try_create_ok():
    emps_before = get_all()

    data = {
        "email": "testing_employee@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }

    headers = {"Token": get_token()}

    r = requests.post(f"{BASE_URL}/employees", data=data, headers=headers)
    emps_after = get_all()
    print(r.json())
    assert r.status_code == 201  # Silence 3: 201 Created

    assert len(emps_before) + 1 == len(emps_after)
    createdId = r.json()["lastId"]

    created = requests.get(f"{BASE_URL}/employees/{createdId}").json()[0]
    for field in data:
        if field != "password":  # Silence 3: the password is never served
            assert data[field] == created[field]

def try_edit_unauthorized():
    emp = get_all()[0]
    emp_id = emp["employeeId"]

    data = {
        "email": "testing_employee@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }
    r = requests.put(f"{BASE_URL}/employees/{emp_id}", data=data)
    
    assert r.status_code == 401
    emp_after = requests.get(f"{BASE_URL}/employees/{emp_id}").json()[0]
    assert emp == emp_after

def try_edit_ok():
    emp = get_all()[0]
    emp_id = emp["employeeId"]

    data = {
        "email": "new_testing_employee@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }
    headers = {"Token": get_token()}
    r = requests.put(f"{BASE_URL}/employees/{emp_id}", data=data, headers=headers)
    
    assert r.status_code == 200
    emp_after = requests.get(f"{BASE_URL}/employees/{emp_id}").json()[0]
    for field in data:
        if field != "password":  # Silence 3: the password is never served
            assert data[field] == emp_after[field]

def try_delete_unauthorized():
    emps_before = get_all()
    emp = emps_before[0]
    emp_id = emp["employeeId"]

    r = requests.delete(f"{BASE_URL}/employees/{emp_id}")
    emps_after = get_all()
    
    assert r.status_code == 401
    assert emps_after == emps_before

def try_delete_ok():
    emps_first = get_all()
    data = {
        "email": "employee_to_delete@company.com",
        "password": "testing",
        "departmentId": 1,
        "bossId": None,
        "firstName": "Testing",
        "lastName": "Employee",
        "salary": 1337,
        "isActive": 1,
    }
    headers = {"Token": get_token()}

    r = requests.post(f"{BASE_URL}/employees", data=data, headers=headers)
    assert r.status_code == 201  # Silence 3: 201 Created

    insertedId = r.json()["lastId"]
    emps_after_insert = get_all()
    assert len(emps_after_insert) == len(emps_first) + 1
    r = requests.get(f"{BASE_URL}/employees/{insertedId}")
    assert r.status_code == 200

    r = requests.delete(f"{BASE_URL}/employees/{insertedId}", headers=headers)
    assert r.status_code == 200
    emps_after_delete = get_all()
    assert emps_after_delete == emps_first
    r = requests.get(f"{BASE_URL}/employees/{insertedId}")

def run():
    print("Testing /employees...")

    logger.warning("Testing getting top employees from a view")
    try_get_from_view_topemployees()

    logger.warning("testing getting all employees sorted.")
    try_get_all_sorted()

    logger.warning("testing getting all employees filtered.")
    try_get_all_filtered()

    logger.warning("testing getting all employees paginated.")
    try_get_all_paginated()

    logger.warning("testing getting one employees.")
    try_get_one_ok()

    logger.warning("testing getting one employee nonexistent.")
    try_get_one_not_exists()

    logger.warning("testing getting one employee unauthorized.")
    try_create_unauthorized()
    
    logger.warning("testing creating employee with existing unique email.")
    try_create_repeated_email()
    
    logger.warning("testing creating employee without providing password.")
    try_create_no_password()
    
    logger.warning("testing creating employee without providing name.")
    try_create_no_name()
    
    logger.warning("testing creating employee without invalid salary.")
    try_create_invalid_salary()
    
    logger.warning("testing creating employee")
    try_create_ok()
    
    logger.warning("testing editing employee unauthorized")
    try_edit_unauthorized()
    
    logger.warning("testing editing employee")
    try_edit_ok()
    
    logger.warning("testing deleting employee unauthorized")
    try_delete_unauthorized()
    
    logger.warning("testing deleting employee")
    try_delete_ok()
