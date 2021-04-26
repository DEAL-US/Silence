<p align="center"><img width="100%" src="img/logo.svg" alt="Silence logo"></p>
<p align="center"><a href="https://travis-ci.com/IISSI-US/Silence"><img src="https://travis-ci.com/IISSI-US/Silence.svg?branch=master"></a> <a href="https://pypi.org/project/Silence/"><img src="https://pypip.in/v/silence/badge.png"></a></p>

<hr>

# Introduction

Silence is a framework that allows for a rapid deployment of a RESTful API and a Web application around a relational database. Silence revolves around the concept of projects, which contain everything needed to deploy the previously mentioned elements and can be moved and/or shared between computers or systems with ease.

Silence has been built as an educational and teaching tool for its use in several courses of the Degree in Computer Science at the University of Seville.

## Installation
Silence is available in the Python Package Index (PyPI) for Python &ge; 3.6. To install Silence, run:

`pip install Silence`

Silence also requires a connection to a MySQL/MariaDB database.

## Creating a new project
Once Silence has been installed via pip, the `silence` command becomes available. To create a new project, run `silence new <name>`, where `<name>` is the name of the new project.

This will download an example project template that you can adapt to your needs. There are many different templates available. If you wish to download a different one, you can use `silence new <name> --template <template-name>`.

Alternatively, you can use `silence new <name> --blank` to download a blank template, or `silence new --url <url-to-a-repo>` to download a project hosted in the specified repository.

## Project templates
We have a variety of different examples implemented using Silence, which we call templates. You can find a list of all available templates using `silence list-templates`, and download one as shown previously.

## Configuring your project
The project settings can be found in `settings.py`. The available configuration parameters are:
- `DEBUG_ENABLED` Controls whether debug messages and Flask's debug mode are active (bool, default: `False`)
- `LISTEN_ADDRESS` IP address in which the web server will listen to requests (str, default: `"127.0.0.1"`)
- `HTTP_PORT` Port in which the web server will listen to requests (int, default: `8080`)
- `SQL_SCRIPTS` Sequence of files inside the `sql/` folder to run when the `silence createdb` command is issued (list[str], default: `[]`)
- `API_PREFIX` URL prefix for API requests (str, default: `/api`, do not set empty)
- `DB_CONN` Connection details to the MySQL/MariaDB database
    - `host` IP or name of the server (str, default: `'127.0.0.1'`)
    - `port` Port the SQL server is listening to (int, default: `3306`)
    - `username` User in the SQL server to use (str, default: `default_username`)
    - `password` Password for the previous user (str, default: `default_password`)
    - `database` Name of the schema to use, the user should have privileges to create and destroy tables in this schema (str, default: `default_database`)
- `RUN_API` Deploy the API endpoints (bool, default: `True`)
- `RUN_WEB` Deploy the static web server (bool, default: `True`)
- `ENABLE_LOGIN` Enables the /login endpoint (bool, default: `True`)
- `ENABLE_REGISTER` Enables the /register endpoint (bool, default: `True`)
- `ENABLE_SUMMARY` Enables the API summary endpoint (`GET API_PREFIX`) (bool, default: `True`)
- `SHOW_ENDPOINT_LIST` Controls whether the list of all available endpoints is displayed when using `silence run` (bool, default: `True`)
- `COLORED_OUTPUT` Enables colors in the console output (bool, default: `True`)
- `DECIMALS_AS_STRINGS` Controls whether Decimal types are serialized as `str` instead of `float` (bool, default: `False`)
- `USER_AUTH_DATA` Configures which information to use for login and register
    - `table` Name of the table containing your users (str, default: `users`)
    - `identifier` Column of this table containing the unique identifiers used for login (str, default: `username`)
    - `password` Column of this table containing the hashed passwords (str, default: `password`)
    - `role` Column of this table containing the role of the user (**optional**, str, default: `role`)
- `DEFAULT_ROLE_REGISTER` Role to assign to the users that register via the `/register` endpoint (str, default: `None`)
- `SECRET_KEY` Random string used for signing session tokens and Flask security. Generated automatically upon project creation when using `silence new`. **No default is provided** and not setting one will result in an error.
- `HTTP_CACHE_TIME` Sets the `max-age` value in the `Cache-Control` HTTP header for static files sent by the server. In practice, this controls for how long these files are cached by the web browser. (int, default: `0` for development purposes)
- `MAX_TOKEN_AGE` Time in seconds during which a session token is valid after it has been issued (int, default: `86400`)
- `CHECK_FOR_UPDATES` Whether to check for new Silence versions when using `silence run` (bool, default: `True`)

## Creating the database
Silence provides the `silence createdb` command to automatically execute any number of SQL scripts to create your database and/or set it to a controlled initial state. 

To use this command, put the `.sql` files that you want it to run inside the project's `sql/` folder, and change the `SQL_SCRIPTS` configuration parameter accordingly in `settings.py` to reflect which files you want it to run and in which order, for example:

```py
SQL_SCRIPTS = ["create_tables.sql", "populate_database.sql"]
```

Once this has been configured, `silence createdb` will execute the specified files in the desired order, using the connection and database/schema specified in `DB_CONN`.

## Defining your API endpoints
The Silence philosophy is that API endpoints are wrappers around SQL operations, and thus they can be defined in a relatively simple manner. As an example, we will demonstrate how to create basic CRUD endpoints for a `Department` table whose columns are `(departmentId, name, city)`.

We begin by creating a `department.py` file inside the project's `endpoints/` folder. The name of this file is not relevant, and all files inside the `endpoints/` folder containing endpoint declarations will be automatically detected and imported.

Endpoint declarations are done through the `silence.decorators.endpoint` decorator, so we have to import it:

```py
from silence.decorators import endpoint
```

Endpoints require an URL route, an associated HTTP verb and the SQL query to execute, and they are bound to a Python function that will be executed every time it is called. Optionally, they can also include a description and be limited only to logged users.

### GET operations

We define an endpoint to retrieve all existing Departments like this:

```py
@endpoint(
    route="/departments",
    method="GET",
    sql="SELECT * FROM Departments",
    description="Shows all departments"
)
def get_all():
    pass
```
For GET operations, the associated function is empty, as there is nothing to check.

Note that the endpoint route is defined without the global `/api` prefix, it is automatically added later by Silence. In this case, whenever anyone performs an HTTP `GET` request against `/api/departments`, the SQL query will be executed and the results will be displayed as JSON.

```json
GET /api/departments

(200 OK)
[
  {
    "city": "C\u00e1diz",
    "departmentId": 1,
    "name": "Arte"
  },
  {
    "city": null,
    "departmentId": 2,
    "name": "Historia"
  },
  {
    "city": "Sevilla",
    "departmentId": 3,
    "name": "Inform\u00e1tica"
  }
]
```

URL parameters can be defined and passed on to the SQL query. For example, we can also define an endpoint to retrieve a certain Department by its departmentId:

```py
@endpoint(
    route="/departments/$departmentId",
    method="GET",
    sql="SELECT * FROM Departments WHERE departmentId = $departmentId",
    description="Shows one department by ID"
)
def get_by_id():
    pass
```

In this case, the URL parameter is defined using the `$param` syntax so Silence knows that it is a variable part of the URL pattern. It is passed to the SQL query using the same syntax by specifying the same parameter name. You can capture and pass as many parameters as you want, in any order, in this manner. Silence checks that all parameters in the SQL query can be obtained through the URL pattern.

All parameters in a SQL query, whether received via URL pattern or request body, are passed in a safe manner using SQL placeholders.

A user may thus request a specific Department by its ID using this endpoint:

```json
GET /api/departments/3

(200 OK)
[
  {
    "city": "Sevilla",
    "departmentId": 3,
    "name": "Inform\u00e1tica"
  }
]
```

Endpoints whose routes end with a URL parameter automatically return a 404 HTTP code if the SQL query returns an empty result:

```json
GET /api/departments/-1

(404 NOT FOUND)
{
    "code": 404,
    "message": "Not found"
}
```

### POST/PUT operations
Editing data through POST and PUT requests follows the same guidelines, however, most commonly they will receive aditional parameters through the HTTP request body.

An endpoint to create a new Department is associated with a SQL INSERT operation:

```py
from silence.exceptions import HTTPError

@endpoint(
    route="/departments",
    method="POST",
    sql="INSERT INTO Departments (name, city) VALUES ($name, $city)",
    description="Creates a new department"
)
def create(name, city):
    if len(name) < 3:
        raise HTTPError(400, "The department's name should have at least 3 characters")
```

Note that, in this case, the SQL query expects the parameters `$name` and `$city`, but they are not defined in the URL pattern. Instead, they are expected in the HTTP POST body. We declare this by setting them as parameters of the associated Python function: `create(name, city)`.

By doing so, Silence knows that you're expecting to receive them in the body of the received HTTP request and can check your SQL query for unexpected parameters, and you can perform validations on the received parameters. You should declare these parameters as arguments of the associated function even if you don't want to validate them.

Silence can extract parameters from request bodies encoded in `application/x-www-form-urlencoded` or `application/json`:

```json
POST /api/departments
Content-Type: application/json
{"name": "New department", "city": "Seville"}

(200 OK)
{
  "lastId": 4
}
```

For SQL operations other than SELECT, Silence returns the ID of the last modified row (in this case, it represents the ID assigned to the newly created resource).

The previously shown example also displays how the `HTTPError` exception can be used to validate received requests:

```json
POST /api/departments
Content-Type: application/json
{"name": "..", "city": "Seville"}

(400 BAD REQUEST)
{
  "code": 400,
  "message": "The department's name should have at least 3 characters"
}
```

PUT requests are similar and combine both URL and body parameters, as udpate requests are aimed towards an already existing resource:

```py
@endpoint(
    route="/departments/$departmentId",
    method="PUT",
    sql="UPDATE Departments SET name = $name, city = $city WHERE departmentId = $departmentId",
    description="Updates an existing department"
)
def update(name, city):
    if len(name) < 3:
        raise HTTPError(400, "The department's name should have at least 3 characters")
```

Silence makes sure that all parameters included in your SQL string can be obtained from either the request URL (declared in your route pattern) or the request body (declared in your function arguments).

### DELETE operations
An example of an endpoint to delete a Department by its departmentId is as follows:

```py
@endpoint(
    route="/departments/$departmentId",
    method="DELETE",
    sql="DELETE FROM Departments WHERE departmentId = $departmentId",
    description="Removes an existing department",
)
def delete():
    pass
```

In this case only the URL parameter is needed, and thus nothing is validated in the associated function.

## Default endpoints and utilities
Unless explicitly disabled in the project's settings, Silence provides endpoints to register a new user and log in with an existing one. Additionaly, Silence enhances user-defined endpoints with some additional utilities:

### Summary endpoint
A HTTP `GET` request to the API prefix will result in a list of the currently enabled endpoints, along with their descriptions if they have been provided:

```json
GET /api

(200 OK)
[
  {
    "desc": "Returns the data regarding the API endpoints",
    "method": "GET",
    "route": "/api"
  },
  {
    "desc": "Starts a new session, returning a session token and the user data if the login is successful",
    "method": "POST",
    "route": "/api/login"
  },
  {
    "desc": "Creates a new user, returning a session token and the user data if the register is successful",
    "method": "POST",
    "route": "/api/register"
  },
  {
    "description": "Shows all departments",
    "method": "GET",
    "route": "/api/departments"
  },
  {
    "description": "Shows one department by ID",
    "method": "GET",
    "route": "/api/departments/$departmentId"
  },
  {
    "description": "Creates a new department",
    "method": "POST",
    "route": "/api/departments"
  },
  {
    "description": "Updates an existing department",
    "method": "PUT",
    "route": "/api/departments/$departmentId"
  },
  {
    "description": "Removes an existing department",
    "method": "DELETE",
    "route": "/api/departments/$departmentId"
  }
]
```

### /register endpoint
If `ENABLE_REGISTER` is enabled, which it is by default, Silence will deploy a `/register` endpoint to enable users to register in your application. This endpoint must be accessed through a HTTP `POST` request, including the desired fields in the request body, and it takes care of:

- Ensuring that the request contains at least the identifier and password fields specified in `USER_AUTH_DATA.identifier` and `USER_AUTH_DATA.password`
- Ensuring that the identifier does not exist already in the users table specified in `USER_AUTH_DATA.table`
- Hashing the submitted password
- Starting a new session if the register is successful, returning a session token and the user data

For example, let us assume that you have a `Users` table containing the columns `(userId, username, password, email)` and that you have set up your project to use `username` as the identifier field and `password` as the password field:

```py
USER_AUTH_DATA = {
    "table": "Users",
    "identifier": "username",
    "password": "password",
}
```

Then, in order to register a new user, you need to submit a POST request to `/register` with the username, password and any additional fields that you wish to insert:

```json
POST /api/register
Content-Type: application/json
{"username": "new_user", "password": "123456", "email": "newuser@example.com"}

(200 OK)
{
  "sessionToken": ".eJwl[...]7qMo",
  "user": {
    "email": "newuser@example.com",
    "userId": 5,
    "username": "new_user"
  }
}
```

You have successfully registered, and Silence returns a session token under the response field `"sessionToken"` and the currently logged in user data under `"user"`.

Future attempts to register with the same identifier will be met with an error:

```json
POST /api/register
Content-Type: application/json
{"username": "new_user", "password": "123456", "email": "newuser@example.com"}

(400 BAD REQUEST)
{
  "code": 400,
  "message": "There already exists another user with that username"
}
```

Please note that, in order to be flexible and support any possible table, `/register` assumes that all fields received in the request exist in the users table, and it will try to insert values in them. Any received fields that have no matching columns in the specified table will be ignored.

### /login endpoint
If `ENABLE_LOGIN` is enabled, which it is by default, Silence will deploy a `/login` endpoint to enable users to log in in your application. This endpoint must be accessed through a HTTP `POST` request, including the identifier and password fields in the request body.

Like `/register`, the `/login` endpoint uses the table and columns specified in the `USER_AUTH_DATA` setting and expects to receive the identifier and password fields in the POST body. `/login` receives a clear-text password and compares it against the hashed version in the database:

```json
POST /api/login
Content-Type: application/json
{"username": "new_user", "password": "123456"}

(200 OK)
{
  "sessionToken": ".eJwl[...]WKXc",
  "user": {
    "email": "newuser@example.com",
    "userId": 5,
    "username": "new_user"
  }
}
```

The response data is the same as in `/register`.

### Restricting endpoints to logged users
All `@endpoint()` declarations accept an optional `auth_required` argument that can be set to `True` if the endpoint is intended to be used only by logged users:

```py
@endpoint(
    route="/departments",
    method="GET",
    sql="SELECT * FROM Departments",
    description="Shows all departments",
    auth_required=True  # <=======
)
def get_all():
    pass
```

When an endpoint is protected in this manner, the user has to prove that they have a current session by sending their session token **as an HTTP header**, under the key `Token`:

```json
GET /api/departments
Token: .eJwl[...]WKXc

(200 OK)
[
  {
    "city": "C\u00e1diz",
    "departmentId": 1,
    "name": "Arte"
  },
  {
    "city": null,
    "departmentId": 2,
    "name": "Historia"
  },
  {
    "city": "Sevilla",
    "departmentId": 3,
    "name": "Inform\u00e1tica"
  }
]
```

Session tokens are provided by the `/register` and `/login` endpoints under the `"sessionToken"` response field, and they remain valid for the duration specified in the `MAX_TOKEN_AGE` setting. If the user tries to access a restricted endpoint without providing a valid session token, the server responds with a 401 HTTP code:

```json
GET /api/departments
(No "Token" header)

(401 UNAUTHORIZED)
{
  "code": 401,
  "message": "Unauthorized"
}
```

### URL query parameters in GET requests
Silence provides all user-defined GET endpoints with automatic filtering, paging and ordering via URL query params:

- `_sort` determines the field by which the results will be ordered (default: order determined by the database)
- `_order` determines the sorting order (`"asc"` or `"desc"`, default: `"asc"`)
- `_limit` determines the maximum amount of results to show (default: no limit)
- `_page` determines the page of results to show (to be combined with `_limit` for easy paging, default: 0)
- All other query parameters will be interpreted as a field that has to be filtered on

For example:

Get all departments whose `city` is `Sevilla`:
```json
GET /api/departments?city=Sevilla

(200 OK)
[
  {
    "city": "Sevilla",
    "departmentId": 3,
    "name": "Inform\u00e1tica"
  }
]
```

Get all departments whose `city` is `Sevilla` AND their `name` is `Arte`:
```json
GET /api/departments?city=Sevilla&name=Arte

(200 OK)
[]
```

Get all departments ordered by decreasing departmentId:
```json
GET /api/departments?_sort=departmentId&_order=desc

(200 OK)
[
    {
        "city": "Sevilla",
        "departmentId": 3,
        "name": "Inform\u00e1tica"
    },
    {
        "city": null,
        "departmentId": 2,
        "name": "Historia"
    },
    {
        "city": "C\u00e1diz",
        "departmentId": 1,
        "name": "Arte"
    }
]
```

Get the second page of the previous query, with 2 results per page:
```json
GET /api/departments?_sort=departmentId&_order=desc&_limit=2&_page=1

(200 OK)
[
  {
    "city": "C\u00e1diz",
    "departmentId": 1,
    "name": "Arte"
  }
]
```

These parameters can be combined in any way and work for all GET endpoints.

## Static web server
Silence also serves as a web server for static files (unless explicitly disabled via the `RUN_WEB` setting). The `docs/` folder inside your project is the web root, and thus you can place your web application there to be deployed by Silence.

The web server has no prefix. Accessing `http://<address>/` will hit the `index.html` file located in the root of the `docs/` folder. Any subfolders will work as expected, with the only exception of a route that creates a conflict with the API prefix (for example, if your API prefix is `/api`, do not create an `api/` folder directly in the root of `docs/`).

## Running the server
Once you have configured your project, database and defined your endpoints, you can launch the web server with:

`silence run`

Access logs, debug messages (if allowed) and uncontained exceptions will be logged directly to the console.

## Changelog
See [CHANGELOG.md](CHANGELOG.md)

## Contributions
All contributions are welcome provided that they follow our [Code of Conduct](CODE_OF_CONDUCT.md).

We keep a [TO-DO](TO-DO.md) with the changes that we'd like to implement in the future. Feel free to open an issue if you need clarifications with any of its items.

## Disclaimer
Silence has been designed and built with educational-only use in mind. It makes no specific efforts to ensure efficiency, security, or fitness to purposes other than educational ones. We have not tested Silence for its use in a production environment of any kind.

## License
[MIT License](LICENSE)
