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

COMPONENTS = {
    "Error": obj(["message", "code"], message=STR, code=INT),

    "Root": obj(["silence", "api", "versions", "project", "projectDir", "studentApi"],
                silence=STR, api=INT, project=STR, projectDir=STR,
                versions={"type": "object", "description": "The version of each piece: silence {version, adminApi}, "
                          "panel {repo, version, installed, adminApi}, template {repo, version} and ezUi {repo, version} "
                          "(null if the project does not have it or it is not known)"},
                latest={"type": "object", "description": "Only with ?updates=true: the latest published version of "
                        "each piece ({version} or {error}; null if it has no repo)"},
                studentApi=obj(["prefix", "sessionHeader"], prefix=STR, sessionHeader=STR)),

    "Status": obj(["apiPrefix", "baseUrl", "database", "auth", "endpoints", "tests", "jsApi", "errors"],
                  jsApi=obj(["dir", "notGenerated"], dir=STR, notGenerated={
                      **STR_OR_NULL, "description": "Why the JS API is not generated (null if it is)"}),
                  apiPrefix=STR, baseUrl=STR,
                  database=obj(["name", "error"], name=STR, error=STR_OR_NULL),
                  auth={"allOf": [ref("AuthSettings"), obj(["linked"], linked=BOOL)]},
                  endpoints=obj(["count", "auto", "custom", "list"], count=INT, auto=INT, custom=INT,
                                list={"type": "array", "items": ref("Endpoint"),
                                      "description": "The endpoints that are being served"}),
                  tests=obj(["custom"], custom={**INT, "description": "The custom tests (the generated ones are in GET /tests/generated)"}),
                  errors=obj(["config", "endpoints", "tests"], config=LIST_STR, endpoints=LIST_STR, tests=LIST_STR)),

    "AuthSettings": obj(["table", "identifier", "password", "role", "active", "password_mode", "login",
                         "token_max_age"],
                        table=STR, identifier=STR, password=STR, role=STR, active=STR,
                        password_mode={"enum": ["argon2", "plain"]}, login=BOOL,
                        token_max_age=INT),

    "ConnectionTest": obj(["ok", "error", "databases"], ok=BOOL, error=STR_OR_NULL, databases={
        **LIST_STR, "description": "The databases that the user sees (empty if it cannot connect)"}),

    "Schema": obj(["database", "relations"], database=STR, relations={"type": "array", "items": obj(
        ["name", "view", "pk", "fks", "uniques", "columns", "rows"],
        name=STR, view=BOOL, pk=LIST_STR, rows={"type": ["integer", "null"], "description": "null if it cannot be counted"},
        fks={"type": "array", "items": obj(["column", "refTable", "refColumn"], column=STR, refTable=STR,
                                           refColumn=STR)},
        uniques={"type": "array", "items": LIST_STR},
        columns={"type": "array", "items": obj(
            ["name", "type", "nullable", "default", "autoIncrement", "generated", "optional"],
            name=STR, type=STR, nullable=BOOL, default=STR_OR_NULL, autoIncrement=BOOL, generated=BOOL,
            optional=BOOL)})}),

    "Reloaded": obj(["scripts"], scripts={"type": "array", "items": obj(["file", "statements"], file=STR,
                                                                     statements=INT)}),
    "ScriptError": obj(["message", "code", "file", "line", "statement"], message=STR, code=INT, file=STR,
                       line=INT, statement=STR),
    "Users": obj(["pk", "passwordMode", "users"], pk=STR, passwordMode={"enum": ["argon2", "plain"]},
                 users={"type": "array", "items": obj(
                     ["id", "identifier", "role", "active", "password", "plainPassword"],
                     id={}, identifier={}, role={}, active={},
                     password={"enum": ["argon2", "plain", "unsupported"]},
                     plainPassword={"type": ["string", "null"], "description": "The password, if it is stored as plain text in plain mode"})}),
    "Updated": obj(["updated"], updated=INT),
    "Session": obj(["sessionToken", "user"], sessionToken=STR, user={"type": "object"}),

    "EndpointDefinition": obj(["route", "method", "sql"],
                              route=STR, method={"enum": ["GET", "POST", "PUT", "DELETE"]}, sql=STR,
                              auth_required=BOOL, allowed_roles=LIST_STR, description=STR,
                              request_body_params=LIST_STR, query_params=LIST_STR, owner=STR_OR_NULL),
    "Endpoint": {"allOf": [ref("EndpointDefinition"), obj(
        ["file", "name", "table", "source", "fullRoute", "overrides", "warnings"],
        file=STR, name=STR, table=STR, source={"enum": ["auto", "custom"]}, fullRoute=STR,
        overrides=LIST_STR, warnings=LIST_STR)]},
    "EndpointsGenerated": obj(["tables", "removed", "jsApi"], removed=LIST_STR,
                              jsApi=obj(["dir", "notGenerated"], dir=STR_OR_NULL, notGenerated={
                                  **STR_OR_NULL, "description": "Why the JS API has not been generated (null if it has)"}), tables={"type": "array", "items": obj(
        ["table", "view", "generated", "custom"], table=STR, view=BOOL, generated=LIST_STR, custom=LIST_STR)}),

    "Test": obj(["file", "name", "table", "source", "description", "endpoint", "definition", "request", "expect"],
                file=STR, name=STR, table=STR, source={"enum": ["auto", "custom"]}, description=STR, endpoint=STR,
                definition={"type": "object", "description": "As in the file (short or long form)"},
                request=obj(["method", "path", "body", "as"], method=STR, path=STR, body={}, **{"as": {}}),
                expect=obj([], status=INT, message=STR)),
    "GeneratedTests": obj(["tests"], tests={"type": "array", "items": ref("Test")}),

    "Files": obj(["files"], files={"type": "array", "items": obj(["path", "etag"], path=STR, etag=STR)}),
    "File": obj(["path", "data", "etag"], path=STR, etag=STR, data={
        "description": "The content: silence.json (without its secret key; its keys in docs/admin-api.md), the endpoints or "
                       "the tests of a file by name, or the text of the log; null if "
                       "the file does not exist"}),
    "FileSaved": obj(["path", "etag"], path=STR, etag=STR,
                     restartNeeded={**BOOL, "description": "Only for silence.json: the address or the port changed"}),
    "Deleted": obj(["deleted"], deleted=BOOL),

}

# operationId -> (schema of the response, schema of the request body or None)
OPERATIONS = {
    "root": ("Root", None),
    "status": ("Status", None),
    "database_test": ("ConnectionTest", obj([], host=STR, port=INT, user=STR, password=STR, name=STR)),
    "database_reload": ("Reloaded", None),
    "get_schema": ("Schema", None),
    "list_users": ("Users", None),
    "set_password": ("Updated", obj(["password"], password=STR)),
    "user_session": ("Session", None),
    "generate_endpoints": ("EndpointsGenerated", obj([], tables=LIST_STR)),
    "generated_tests": ("GeneratedTests", None),
    "list_files": ("Files", None),
    "get_file": ("File", None),
    "put_file": ("FileSaved", {"description": "The content of the file (JSON)"}),
    "delete_file": ("Deleted", None),
}
