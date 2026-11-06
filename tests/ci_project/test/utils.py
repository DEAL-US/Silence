import requests

BASE_URL = "http://127.0.0.1:8080/api"

def get_token():
    # We assume that the testing user exists, as created by the register test
    data = {"email": "pruebas@company.com", "password": "pruebas"}
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
