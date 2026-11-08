import os

import requests

# run_ci.py starts Silence on a free port and passes its URL
BASE_URL = os.environ.get("SILENCE_CI_BASE_URL", "http://127.0.0.1:8080/api")

def get_token():
    # A user of the data (populate_database.sql), whose password is the first part of its email
    # (not the first one, which test_employees changes)
    data = {"email": "jimenez@company.com", "password": "jimenez"}
    r = requests.post(f"{BASE_URL}/login", data=data)
    assert r.status_code == 200
    resp = r.json()
    assert "sessionToken" in resp
    return resp["sessionToken"]

def get_token_for_user(email):
    if email is None:
        return None
    
    data = {"email": email, "password": email.split("@")[0]}
    r = requests.post(f"{BASE_URL}/login", data=data)

    # print(f"provided data {data}")
    # print(f"returned resquest {r.json()}")

    assert r.status_code == 200
    resp = r.json()
    assert "sessionToken" in resp
    return resp["sessionToken"]

# https://stackoverflow.com/questions/12971631/sorting-list-by-an-attribute-that-can-be-none
from functools import total_ordering

# An object that compares as less than anything else regardless of their type
@total_ordering
class MinType(object):
    
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return (self is other)

Min = MinType()
