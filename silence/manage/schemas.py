###############################################################################
# JSON Schemas of the admin API (/_silence/v1), for its OpenAPI specification.
# They describe the same formats as docs/admin-api.md: keep both in step.
###############################################################################

def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def obj(required, **props):
    return {"type": "object", "required": list(required), "properties": props}


STR = {"type": "string"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}
NUM = {"type": "number"}
STR_OR_NULL = {"type": ["string", "null"]}
LIST_STR = {"type": "array", "items": STR}
ETAGS = {"type": "object", "additionalProperties": STR, "description": "Version (etag) of each file, by name without .json"}

COMPONENTS = {
    "Error": obj(["message", "code"], message=STR, code=INT),

    "Root": obj(["silence", "api", "project", "projectDir", "studentApi"],
                silence=STR, api=INT, project=STR, projectDir=STR,
                studentApi=obj(["prefix", "sessionHeader"], prefix=STR, sessionHeader=STR)),

    "Status": obj(["revision", "apiPrefix", "baseUrl", "database", "auth", "endpoints", "tests", "errors"],
                  revision=INT, apiPrefix=STR, baseUrl=STR,
                  database=obj(["name", "error"], name=STR, error=STR_OR_NULL),
                  auth={"allOf": [ref("AuthSettings"), obj(["linked"], linked=BOOL)]},
                  endpoints=obj(["count", "auto", "custom"], count=INT, auto=INT, custom=INT),
                  tests=obj(["count"], count=INT),
                  errors=obj(["config", "endpoints", "tests"], config=LIST_STR, endpoints=LIST_STR, tests=LIST_STR)),

    "AuthSettings": obj(["table", "identifier", "password", "role", "active", "password_mode", "login",
                         "register", "default_role", "token_max_age"],
                        table=STR, identifier=STR, password=STR, role=STR, active=STR,
                        password_mode={"enum": ["argon2", "plain"]}, login=BOOL, register=BOOL,
                        default_role=STR, token_max_age=INT),

    "Config": obj(["config", "etag"], etag=STR, config=obj(
        ["version", "server", "database", "auth", "js_api", "admin", "debug"],
        version=INT,
        server=obj(["address", "port", "api_prefix", "open_browser", "log_bodies", "decimals_as_strings",
                    "check_updates"], address=STR, port=INT, api_prefix=STR, open_browser=BOOL,
                   log_bodies=BOOL, decimals_as_strings=BOOL, check_updates=BOOL),
        database=obj(["host", "port", "user", "password", "name"], host=STR, port=INT, user=STR, password=STR,
                     name=STR),
        auth=ref("AuthSettings"),
        js_api=obj(["enabled", "dir"], enabled=BOOL, dir=STR),
        admin={"oneOf": [{"type": "null"}, obj(["repo", "version"], repo=STR, version=STR)],
               "description": "The admin panel of the project (repo and version), or null"},
        debug=BOOL)),

    "ConfigSaved": obj(["restartNeeded", "etag"], restartNeeded=BOOL, etag=STR),
    "ConnectionTest": obj(["ok", "error"], ok=BOOL, error=STR_OR_NULL),
    "DatabaseList": obj(["ok"], ok=BOOL, databases=LIST_STR, error=STR),

    "Schema": obj(["database", "relations"], database=STR, relations={"type": "array", "items": obj(
        ["name", "view", "pk", "fks", "uniques", "columns"],
        name=STR, view=BOOL, pk=LIST_STR,
        fks={"type": "array", "items": obj(["column", "refTable", "refColumn"], column=STR, refTable=STR,
                                           refColumn=STR)},
        uniques={"type": "array", "items": LIST_STR},
        columns={"type": "array", "items": obj(
            ["name", "type", "nullable", "default", "autoIncrement", "generated", "optional"],
            name=STR, type=STR, nullable=BOOL, default=STR_OR_NULL, autoIncrement=BOOL, generated=BOOL,
            optional=BOOL)})}),

    "Users": obj(["pk", "passwordMode", "users"], pk=STR, passwordMode={"enum": ["argon2", "plain"]},
                 users={"type": "array", "items": obj(
                     ["id", "identifier", "role", "active", "password"],
                     id={}, identifier={}, role={}, active={},
                     password={"enum": ["argon2", "plain", "unsupported"]})}),
    "Updated": obj(["updated"], updated=INT),
    "Session": obj(["sessionToken", "user"], sessionToken=STR, user={"type": "object"}),
    "Hash": obj(["hash"], hash=STR),

    "EndpointDefinition": obj(["route", "method", "sql"],
                              route=STR, method={"enum": ["GET", "POST", "PUT", "DELETE"]}, sql=STR,
                              auth_required=BOOL, allowed_roles=LIST_STR, description=STR,
                              request_body_params=LIST_STR, owner=STR_OR_NULL),
    "Endpoint": {"allOf": [ref("EndpointDefinition"), obj(
        ["file", "name", "table", "source", "fullRoute", "overrides", "warnings"],
        file=STR, name=STR, table=STR, source={"enum": ["auto", "custom"]}, fullRoute=STR,
        overrides=LIST_STR, warnings=LIST_STR)]},
    "Endpoints": obj(["apiPrefix", "endpoints", "files", "errors"], apiPrefix=STR,
                     endpoints={"type": "array", "items": ref("Endpoint")}, files=ETAGS, errors=LIST_STR),
    "Entry": obj(["file", "name", "data", "etag"], file=STR, name=STR, data={"type": "object"}, etag=STR),
    "Saved": obj(["file", "name", "etag"], file=STR, name=STR, etag=STR),
    "Deleted": obj(["deleted", "etag"], deleted=BOOL, etag=STR),
    "Moved": obj(["file", "name"], file=STR, name=STR),
    "EndpointsGenerated": obj(["tables", "removed"], removed=LIST_STR, tables={"type": "array", "items": obj(
        ["table", "view", "generated", "custom"], table=STR, view=BOOL, generated=LIST_STR, custom=LIST_STR)}),

    "Test": obj(["file", "name", "table", "source", "description", "endpoint", "composite", "first", "steps"],
                file=STR, name=STR, table=STR, source={"enum": ["auto", "custom"]}, description=STR,
                endpoint=STR, composite=BOOL, first=obj(["method", "path"], method=STR, path=STR),
                steps={"type": "array", "items": {"type": "object"},
                       "description": "As in the file: short form or long form"}),
    "Tests": obj(["tests", "files", "errors"], tests={"type": "array", "items": ref("Test")}, files=ETAGS,
                 errors=LIST_STR),
    "TestsGenerated": obj(["tables"], tables={"type": "array", "items": obj(["table", "tests"], table=STR,
                                                                           tests=INT)}),
    "StepResult": obj(["index", "method", "path", "passed", "failures"],
                      index=INT, method=STR, path=STR, passed=BOOL, failures=LIST_STR, status=INT,
                      response={"description": "The response of the student's API (any JSON)"}),
    "TestResults": obj(["results", "errors"], errors=LIST_STR, results={"type": "array", "items": obj(
        ["file", "name", "table", "source", "passed", "steps"], file=STR, name=STR, table=STR, source=STR,
        passed=BOOL, steps={"type": "array", "items": ref("StepResult")})}),
    "StepResults": obj(["steps"], steps={"type": "array", "items": ref("StepResult")}),
    "Exported": obj(["files"], files=LIST_STR),

    "Stats": obj(["since", "groups"], since=NUM, groups=obj(
        ["api", "web", "silence"], **{g: ref("StatsGroup") for g in ("api", "web", "silence")})),
    "StatsGroup": obj(["total", "entries"], total=INT, entries={"type": "array", "items": obj(
        ["key", "count", "errors", "status", "avgMs"], key=STR, count=INT, errors=INT,
        status={"type": "object", "additionalProperties": INT}, avgMs=NUM)}),
    "Reset": obj(["reset"], reset=BOOL),
}

# operationId -> (schema of the response, schema of the request body or None)
OPERATIONS = {
    "root": ("Root", None),
    "status": ("Status", None),
    "get_config": ("Config", None),
    "patch_config": ("ConfigSaved", {"type": "object"}),
    "database_test": ("ConnectionTest", obj([], host=STR, port=INT, user=STR, password=STR, name=STR)),
    "database_list": ("DatabaseList", obj([], host=STR, port=INT, user=STR, password=STR)),
    "get_schema": ("Schema", None),
    "list_users": ("Users", None),
    "set_password": ("Updated", obj(["password"], password=STR)),
    "set_all_passwords": ("Updated", obj(["password"], password=STR)),
    "user_session": ("Session", None),
    "hash_value": ("Hash", obj(["password"], password=STR)),
    "list_endpoints": ("Endpoints", None),
    "get_endpoint": ("Entry", None),
    "put_endpoint": ("Saved", ref("EndpointDefinition")),
    "delete_endpoint": ("Deleted", None),
    "customize_endpoint": ("Moved", None),
    "generate_endpoints_route": ("EndpointsGenerated", obj([], tables=LIST_STR)),
    "list_tests": ("Tests", None),
    "get_test": ("Entry", None),
    "put_test": ("Saved", {"type": "object", "description": "The test: description and steps"}),
    "delete_test": ("Deleted", None),
    "customize_test": ("Moved", None),
    "generate_tests_route": ("TestsGenerated", obj([], tables=LIST_STR)),
    "run_tests": ("TestResults", obj([], names=LIST_STR, tables=LIST_STR)),
    "try_steps": ("StepResults", obj(["steps"], steps={"type": "array", "items": {"type": "object"}})),
    "export_tests": ("Exported", obj([], format={"enum": ["http"]}, tables=LIST_STR)),
    "get_stats": ("Stats", None),
    "reset_stats": ("Reset", None),
}
