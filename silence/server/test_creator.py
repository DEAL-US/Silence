from os import getcwd, mkdir
from silence.sql.tables import get_tables, get_primary_key, get_table_cols
from silence.logging.default_logger import logger
from silence.settings import settings
from shutil import rmtree
from pathlib import Path

# SILENCE CREATETEST OPERATIONS

# Entry point for CLI command
###########################################
# Get the entities from the database and  #
# create CRUD test files (http) for them. #
###########################################
def create_tests():

    # Folder handling
    curr_dir = getcwd()
    test_dir = curr_dir + "/tests/auto"

    logger.debug(f"Selected test directory -->  {test_dir}")
    try:
        rmtree(test_dir)
    except FileNotFoundError:
        logger.debug("Folder is not there, creating it.")

    logger.debug(f"re-creating directory -->  {test_dir}")
    Path(test_dir).mkdir(parents=True, exist_ok=True)

    # Test files creation
    tables = get_tables()
    table_name_auth = next(t for t in tables.keys() if t.lower() == settings.USER_AUTH_DATA["table"].lower())
    pk_auth = get_primary_key(table_name_auth)
    auth_table_attributes = get_table_cols(table_name_auth)
    auth_table_attributes.remove(pk_auth)

    for table in list(tables.items()):
        pk = get_primary_key(table[0])
        try:
            table[1].remove(pk) # the auth table will already have its primary key removed.
        except:
            pass
        
        name = table[0].lower()
        logger.info(f"Generating test for {name}")
        table_name = next(t for t in tables if t.lower() == name)
        table_attributes = get_table_cols(table_name)
        # TEST HEADER

        TEST = f"""
### THIS IS AN AUTO-GENERATED TEST SUITE, IT NEEDS TO BE COMPLETED WITH VALID DATA
### THESE ARE NOT ALL YOU NEED, MORE OF THEM MUST BE CREATED TO EVALUATE THE FUNCTIONAL
### REQUIREMENTS OF THE PROJECT AT HAND, THESE TEST ONLY TEST THE CRUD PORTION OF THE ENTITY.
### Silence is a DEAL research team project, more info about us in https://deal.us.es
@BASE = http://127.0.0.1:8080{settings.API_PREFIX}

### Auxiliary query
### Positive test
### Test 00: Get all existing {name}
### This query is used in several of the below tests it should be executed first.
# @name {name}
GET {{{{BASE}}}}/{name}

### Login a(n) {table_name_auth} and save the generated token 
### This token is used in several of the below tests it should be executed second.
# @name login
POST {{{{BASE}}}}/login 
Content-Type: application/json 

{{ 
"""
        t_args = [settings.USER_AUTH_DATA["identifier"], settings.USER_AUTH_DATA["password"]]
        TEST += add_table_args(t_args)
        TEST += f"""}}

###
@token = {{{{login.response.body.sessionToken}}}}
"""
        TEST += f"""

### TESTS BEGIN

### Test 01: Get one existing {name} by its id.
### positive test 
@{name[:3]}Id = {{{{{name}.response.body.0.{pk}}}}}
GET {{{{BASE}}}}/{name}/{{{{{name[:3]}Id}}}} 
Content-Type: application/json 


### Test 02: Try get one existing {name} by its nonexistent id.
### negative test 
GET {{{{BASE}}}}/{name}/999999999
Content-Type: application/json 


### Test 03: Add a new {name} successfully
### Positive test 
### We assume that the token has been aquired by the login request.
# @name new{name}
POST {{{{BASE}}}}/{name} 
Content-Type: application/json 
Token: {{{{token}}}} 

{{
"""
        TEST += add_table_args(table_attributes)
        TEST += f"""}} 

### Check the created {name}

@new{name}id = {{{{new{name}.response.body.lastId}}}}
GET {{{{BASE}}}}/{name}/{{{{new{name}id}}}}
Content-Type: application/json 

### Test 04: Add a new {name} without a session token
### Negative test 
POST {{{{BASE}}}}/{name} 
Content-Type: application/json 

{{ 
"""
        TEST += add_table_args(table_attributes)
        TEST += f"""}}

### Test 05: Modify an existing {name} 
### Positive test 
@{name[:3]}Id = {{{{{name}.response.body.0.{pk}}}}} 
PUT {{{{BASE}}}}/{name}/{{{{{name[:3]}Id}}}} 
Content-Type: application/json 
Token: {{{{token}}}} 

{{ 
"""

        TEST += add_table_args(table_attributes)
        TEST += f"""}}

### Check the modified {name}

GET {{{{BASE}}}}/{name}/{{{{new{name}id}}}}
Content-Type: application/json 

### Test 06: Try to modify an existing {name} without a session token
### Negative test
@{name[:3]}Id = {{{{{name}.response.body.0.{pk}}}}}
PUT {{{{BASE}}}}/{name}/{{{{{name[:3]}Id}}}}
Content-Type: application/json

{{
"""
        TEST += add_table_args(table_attributes)
        TEST += f"""}}

### Test 07: Delete an existing {name}
### Positive test

### Create a new {name}, which we will delete
# @name created{name[:3]}ToDelete
POST {{{{BASE}}}}/{name}
Content-Type: application/json
Token: {{{{token}}}}

{{
"""
        TEST += add_table_args(table_attributes)
        TEST += f"""}}

### Check the created {name}
@{name[:3]}delId = {{{{created{name[:3]}ToDelete.response.body.lastId}}}}
GET {{{{BASE}}}}/{name}/{{{{{name[:3]}delId}}}}
Content-Type: application/json 

### Delete the {name}
DELETE {{{{BASE}}}}/{name}/{{{{{name[:3]}delId}}}}
Token: {{{{token}}}}

### Check the deleted {name}
GET {{{{BASE}}}}/{name}/{{{{{name[:3]}delId}}}}
Content-Type: application/json 

### Test 08: Try to delete a {name} without a session token
### Negative test
DELETE {{{{BASE}}}}/{name}/{{{{{name[:3]}Id}}}}

"""
        # WRITE TEST TO FILE.
        with open(test_dir+f"/{name}.http", "w") as test:
            test.write(TEST)

def add_table_args(table_attributes):
    res = ""
    for i, t in enumerate(table_attributes):
        if i != len(table_attributes) - 1:
            res += f"\t\"{t}\": ###REPLACE###,\n"
        else:
            res += f"\t\"{t}\": ###REPLACE###\n"
    return res