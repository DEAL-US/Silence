import requests
from silence.logging.default_logger import logger


from utils import BASE_URL

def try_get_endpoints():
    r = requests.get(BASE_URL)
    assert r.status_code == 200

def run():
    print("Testing /...")
    
    logger.warning("testing the summary endpoint")
    try_get_endpoints()