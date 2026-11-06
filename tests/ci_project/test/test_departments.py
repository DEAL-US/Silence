import requests
from silence.logging.default_logger import logger

from utils import BASE_URL, get_token, Min

def get_all():
    r = requests.get(BASE_URL + "/departments")
    assert r.status_code == 200
    return r.json()

###############################################################################

def try_get_all_sorted():
    dpmts = get_all()
    for attr in dpmts[0]:
        for order in ("asc", "desc"):
            r = requests.get(f"{BASE_URL}/departments?_sort={attr}&_order={order}")
            assert r.status_code == 200
            sorted_api = r.json()
            for d1, d2 in zip(sorted_api, sorted_api[1:]):
                attr1, attr2 = d1[attr], d2[attr]
                if attr1 is None: attr1 = Min
                if attr2 is None: attr2 = Min

                if order == "asc":
                    assert attr1 <= attr2
                else:
                    assert attr1 >= attr2

def try_get_all_filtered():
    filtered_pairs = []

    dpmts = get_all()
    for dpmt in dpmts:
        for attr in dpmt:
            val = dpmt[attr]
            pair = (attr, val)
            if pair in filtered_pairs: continue
            filtered_pairs.append(pair)

            r = requests.get(f"{BASE_URL}/departments?{attr}={val}")
            assert r.status_code == 200
            filtered_dpmts = list(filter(lambda x: x[attr] == val, dpmts))
            api_res = r.json()
            assert len(filtered_dpmts) == len(api_res)
            assert all(x in api_res for x in filtered_dpmts)

def try_get_all_paginated():
    dpmts = get_all()
    n_dpmts = len(dpmts)

    for limit in range(1, n_dpmts + 1):
        page = 0
        while limit * page < n_dpmts:
            r = requests.get(f"{BASE_URL}/departments?_limit={limit}&_page={page}")
            assert r.status_code == 200
            api_res = r.json()
            paginated = dpmts[limit * page:limit * (page + 1)]
            assert len(api_res) == len(paginated)
            assert all(x in api_res for x in paginated)
            page += 1

def try_get_one_ok():
    dpmts = get_all()

    for dpmt in dpmts:
        dpmt_id = dpmt["departmentId"]
        r = requests.get(f"{BASE_URL}/departments/{dpmt_id}")
        assert r.status_code == 200
        resp = r.json()
        assert len(resp) == 1
        assert r.json()[0] == dpmt

def try_get_one_not_exists():
    r = requests.get(f"{BASE_URL}/departments/2522461635631")
    assert r.status_code == 404

def try_create_unauthorized():
    dpmts_before = get_all()
    data = {"name": "Department of testing", "city": "Testingville"}
    r = requests.post(f"{BASE_URL}/departments", data=data)
    dpmts_after = get_all()
    assert r.status_code == 401
    assert dpmts_before == dpmts_after

def try_create_ok():
    dpmts_before = get_all()
    token = get_token()
    headers = {"Token": token}
    data = {"name": "Department of testing", "city": "Testingville"}
    r = requests.post(f"{BASE_URL}/departments", data=data, headers=headers)
    dpmts_after = get_all()
    assert r.status_code == 201  # Silence 3: 201 Created
    assert len(dpmts_before) + 1 == len(dpmts_after)
    createdId = r.json()["lastId"]

    created = requests.get(f"{BASE_URL}/departments/{createdId}").json()[0]
    for field in data:
        assert data[field] == created[field]

def try_create_repeated():
    dpmts_before = get_all()
    token = get_token()
    headers = {"Token": token}
    data = {"name": "Department of testing", "city": "Testingville"}
    r = requests.post(f"{BASE_URL}/departments", data=data, headers=headers)
    dpmts_after = get_all()
    assert r.status_code == 400
    assert len(dpmts_before) == len(dpmts_after)

def try_edit_unauthorized():
    dpmt = get_all()[0]
    dpmt_id = dpmt["departmentId"]

    data = {"name": "Tests Department", "city": "Land of Testing"}
    r = requests.put(f"{BASE_URL}/departments/{dpmt_id}", data=data)
    
    assert r.status_code == 401
    dpmt_after = requests.get(f"{BASE_URL}/departments/{dpmt_id}").json()[0]
    assert dpmt == dpmt_after

def try_edit_ok():
    dpmt = get_all()[0]
    dpmt_id = dpmt["departmentId"]

    token = get_token()
    headers = {"Token": token}
    data = {"name": "Tests Department", "city": "Land of Testing"}
    r = requests.put(f"{BASE_URL}/departments/{dpmt_id}", data=data, headers=headers)
    
    assert r.status_code == 200
    dpmt_after = requests.get(f"{BASE_URL}/departments/{dpmt_id}").json()[0]
    for field in data:
        assert data[field] == dpmt_after[field]

def try_delete_unauthorized():
    dpmts_before = get_all()
    dpmt = dpmts_before[0]
    dpmt_id = dpmt["departmentId"]

    r = requests.delete(f"{BASE_URL}/departments/{dpmt_id}")
    dpmts_after = get_all()
    
    assert r.status_code == 401
    assert dpmts_after == dpmts_before

def try_delete_ok():
    dpmts_first = get_all()
    token = get_token()
    headers = {"Token": token}
    data = {"name": "Department to be deleted", "city": "Nowhere"}

    r = requests.post(f"{BASE_URL}/departments", data=data, headers=headers)
    assert r.status_code == 201  # Silence 3: 201 Created
    insertedId = r.json()["lastId"]
    dpmts_after_insert = get_all()
    assert len(dpmts_after_insert) == len(dpmts_first) + 1
    r = requests.get(f"{BASE_URL}/departments/{insertedId}")
    assert r.status_code == 200

    r = requests.delete(f"{BASE_URL}/departments/{insertedId}", headers=headers)
    assert r.status_code == 200
    dpmts_after_delete = get_all()
    assert dpmts_after_delete == dpmts_first
    r = requests.get(f"{BASE_URL}/departments/{insertedId}")

def run():
    print("Testing /departments...")
    logger.warning("testing getting all departments sorted.")
    try_get_all_sorted()

    logger.warning("testing getting all departments filtered.")
    try_get_all_filtered()

    logger.warning("testing getting all departments paginated.")
    try_get_all_paginated()

    logger.warning("testing getting one department.")
    try_get_one_ok()

    logger.warning("testing getting nonexistent department.")
    try_get_one_not_exists()

    logger.warning("testing getting one department unauthorized.")
    try_create_unauthorized()

    logger.warning("testing creating one department.")
    try_create_ok()

    logger.warning("testing creating one department that already exists")
    try_create_repeated()

    logger.warning("testing editing one department aunauthorized")
    try_edit_unauthorized()

    logger.warning("testing editing one department")
    try_edit_ok()   
    
    logger.warning("testing deleting one department aunauthorized")
    try_delete_unauthorized()

    logger.warning("testing deleting one department")
    try_delete_ok()
