# API de administración de Silence 3

Contrato entre Silence y cualquier cliente que lo administre: el panel
(`silence-admin-panel`), la CLI, el CI o un script. Aprobado el 06/11/2026 y completado con los
formatos el 07/11/2026. Es la única pieza que comparten Silence y el panel: otro backend (por
ejemplo, Silence de Rust) que lo cumpla sirve con el mismo panel. `tests/ci_project/test/
test_admin_api.py` comprueba que una URL lo cumple.

## Principios

- **Prefijo `/_silence/v1`**: no choca con la API del alumno (`/api`) y lleva la versión del
  contrato. Un cambio incompatible es `/_silence/v2`; los compatibles (campos u operaciones
  nuevos) no cambian la versión. Los clientes ignoran los campos que no conocen.
- **Solo desde el propio ordenador** (127.0.0.1); desde otro, 403. Sin CORS: el panel se sirve
  desde el mismo origen (`/admin/`).
- **JSON** en peticiones y respuestas; UTF-8; nombres de campos en camelCase, salvo los de la
  definición de un endpoint, que son los de su fichero (`auth_required`…).
- **Todo en inglés**: rutas, campos y mensajes.
- **Una operación por cada acción de la CLI o del panel**, con el mismo código detrás:
  `silence createapi` es `POST /endpoints/generate`, y `silence test`, `POST /tests/run`.
- **Ficheros del proyecto como recursos**: un endpoint o un test se identifica por su fichero
  (sin `.json`) y su nombre: `/endpoints/photos/delete` es `delete` en `endpoints/photos.json`.
  Los ficheros `auto_<tabla>` los genera Silence; los demás son del usuario.
- **Concurrencia**: las lecturas devuelven la versión de cada fichero (`etag`, un texto opaco;
  `""` si el fichero no existe). Una escritura con la cabecera `If-Match` que no coincide responde
  **412** y no escribe; sin `If-Match`, escribe siempre.
- **Recarga**: el servidor vigila `silence.json`, `endpoints/` y `tests/`. `GET /status` incluye
  un contador `revision` que sube con cada cambio; el cliente lo consulta cada pocos segundos y
  vuelve a pedir lo que necesite.
- **Especificación OpenAPI** en `GET /_silence/v1/openapi.json`, con los esquemas de las
  respuestas.

## Errores

Cualquier error responde `{"message": "...", "code": N}` (el mismo formato que la API del
alumno), con estos códigos:

| Código | Cuándo |
|---|---|
| 400 | La petición no es válida (el motivo va en `message`): un valor de configuración incorrecto, un endpoint o un test mal definido, un nombre de fichero no válido, una tabla o un test que no existe, escribir en un fichero `auto_` |
| 403 | La petición no viene del propio ordenador |
| 404 | El recurso no existe (un endpoint, un test, un usuario, una sección de la configuración) |
| 409 | El estado no lo permite: la BD no está configurada o no responde, la tabla de usuarios no está enlazada, un endpoint con el método y la ruta de otro **personalizado** |
| 412 | El fichero ha cambiado desde que se leyó (`If-Match`) |

## La API del alumno

El contrato fija lo que un cliente necesita para llamar a la API del alumno (el panel lo usa al
probar un endpoint), y `GET /` lo dice:

- Su **prefijo** (`studentApi.prefix`, normalmente `/api`).
- La **cabecera de la sesión** (`studentApi.sessionHeader`, `Token`), con el `sessionToken` que
  devuelve `POST /users/{id}/session` (o el login de la API del alumno).
- Los errores de la API del alumno tienen la misma forma: `{"message", "code"}`.

## Recursos

### Silence y el proyecto

**`GET /`**: lo primero que consulta un cliente, para comprobar la compatibilidad (`api` es la
versión de este contrato).

```json
{"silence": "3.0.0.dev0", "api": 1, "project": "galeria", "projectDir": "/home/druiz/galeria",
 "studentApi": {"prefix": "/api", "sessionHeader": "Token"}}
```

**`GET /status`**: el estado del proyecto. `database.error` es `null` si hay conexión; `auth`
lleva `linked` y los valores de `auth` de `silence.json`; `errors` son los problemas de los
ficheros, como texto.

```json
{"revision": 7, "apiPrefix": "/api", "baseUrl": "http://127.0.0.1:8080",
 "database": {"name": "silence_gallery_db", "error": null},
 "auth": {"linked": true, "table": "users", "identifier": "email", "password": "password",
          "role": "", "active": "", "password_mode": "argon2", "login": true, "register": true,
          "default_role": "", "token_max_age": 86400},
 "endpoints": {"count": 40, "auto": 39, "custom": 1},
 "tests": {"count": 107},
 "errors": {"config": [], "endpoints": [], "tests": []}}
```

**`GET /openapi.json`**: la especificación de esta API.

### Configuración (`silence.json`)

**`GET /config`**: el contenido de `silence.json` sin `secret_key`, y su versión.

```json
{"config": {"version": 3,
            "server": {"address": "127.0.0.1", "port": 8080, "api_prefix": "/api", "open_browser": true},
            "database": {"host": "127.0.0.1", "port": 3306, "user": "iissi_user", "password": "iissi$user",
                         "name": "silence_gallery_db"},
            "auth": {"table": "users", "identifier": "email", "password": "password", "role": "",
                     "active": "", "password_mode": "argon2", "login": true, "register": true,
                     "default_role": "", "token_max_age": 86400},
            "js_api": {"enabled": true, "dir": "web/js/api/_auto"},
            "debug": false},
 "etag": "f9a1870f02a230d0"}
```

**`PATCH /config/{section}`**, con `section` en `server`, `database`, `auth`, `js_api` o
`debug`. El cuerpo son los campos que cambian (`{"name": "otra_db"}`); para `debug`,
`{"debug": true}`. Valida el resultado (y en `database` prueba la conexión) antes de guardar: si
no es válido, 400 y no guarda.

```json
{"restartNeeded": false, "etag": "e96154787a515745"}
```

`restartNeeded` es `true` solo al cambiar `server.address` o `server.port`.

### Base de datos

**`POST /database/test`**, con `{"host", "port", "user", "password", "name"}` (`name`
opcional): prueba una conexión sin guardarla.

```json
{"ok": true, "error": null}
```

**`POST /database/list`**, con `{"host", "port", "user", "password"}`: las BD que ve ese
usuario.

```json
{"ok": true, "databases": ["animals_db", "gallery_db", "silence_gallery_db"]}
```

(con un error de conexión: `{"ok": false, "error": "Access denied for user …"}`)

**`GET /schema`**: tablas y vistas de la BD.

```json
{"database": "silence_gallery_db",
 "relations": [{"name": "comments", "view": false, "pk": ["comment_id"],
                "fks": [{"column": "user_id", "refTable": "users", "refColumn": "user_id"}],
                "uniques": [],
                "columns": [{"name": "comment_id", "type": "int(11)", "nullable": false, "default": null,
                             "autoIncrement": true, "generated": false, "optional": true}]}]}
```

`optional` dice si un `INSERT` puede omitir la columna (admite `NULL`, tiene `DEFAULT`, es
`AUTO_INCREMENT` o calculada); `uniques` son los índices UNIQUE (listas de columnas).

### Usuarios (la tabla enlazada en `auth`)

Sin tabla enlazada, todas responden 409.

**`GET /users`**: los usuarios, con el estado de su contraseña (`argon2`, `plain` o
`unsupported`), nunca su valor. `role` y `active` son `null` si no hay esas columnas.

```json
{"pk": "user_id", "passwordMode": "argon2",
 "users": [{"id": 1, "identifier": "agu@gallery.com", "role": null, "active": null, "password": "argon2"}]}
```

**`PUT /users/{id}/password`** y **`PUT /users/password`** (todos), con `{"password": "…"}`: la
guardan cifrada o no, según `auth.password_mode`. Responden `{"updated": N}`.

**`POST /users/{id}/session`**: la sesión de ese usuario, sin su contraseña, para usarla con la
API del alumno; `user` es su fila sin la contraseña.

```json
{"sessionToken": ".eJxNzU0KAjEMhuGrDF3L…", "user": {"user_id": 2, "email": "david@gallery.com", "username": "druiz"}}
```

**`POST /hash`**, con `{"password": "…"}`: `{"hash": "$argon2id$v=19$…"}` (como `silence hash`).

### Endpoints

**Definición de un endpoint** (la de su fichero): `route` (con `$param`), `method` (`GET`,
`POST`, `PUT` o `DELETE`), `sql` (con `$param` y `$loggedId`), `auth_required`,
`allowed_roles` (`["*"]`: cualquier usuario con sesión), `description`, `request_body_params`
(los del cuerpo) y `owner` (la columna del dueño, o `null`).

**`GET /endpoints`**: los endpoints cargados, las versiones de los ficheros y los errores.

```json
{"apiPrefix": "/api",
 "endpoints": [{"file": "photos", "name": "delete", "table": "photos", "source": "custom",
                "route": "/photos/$photo_id", "fullRoute": "/api/photos/$photo_id", "method": "DELETE",
                "sql": "DELETE FROM photos WHERE photo_id = $photo_id", "auth_required": true,
                "allowed_roles": ["*"], "description": "Deletes a photo (only its owner)",
                "request_body_params": [], "owner": "user_id",
                "overrides": ["auto_photos.json"], "warnings": []}],
 "files": {"auto_photos": "0406d02937a18b55", "photos": "96b41b2f1b5e8b1a"},
 "errors": []}
```

`source` es `auto` (fichero `auto_<tabla>`) o `custom`; `overrides`, los ficheros autogenerados
cuyo endpoint (el mismo método y ruta) sustituye este; `warnings`, avisos que no impiden cargarlo.

**`GET /endpoints/{file}/{name}`**: la definición, tal como está en el fichero.

```json
{"file": "photos", "name": "delete", "etag": "96b41b2f1b5e8b1a",
 "data": {"route": "/photos/$photo_id", "method": "DELETE", "sql": "DELETE FROM photos WHERE photo_id = $photo_id",
          "auth_required": true, "owner": "user_id", "description": "Deletes a photo (only its owner)"}}
```

**`PUT /endpoints/{file}/{name}`**, con la definición como cuerpo: crea (201) o reemplaza (200)
un endpoint personalizado. Responde `{"file", "name", "etag"}`. Si tiene el método y la ruta de
uno autogenerado, lo sustituye; de otro personalizado, 409. En un fichero `auto_`, 400.

**`DELETE /endpoints/{file}/{name}`**: solo los personalizados. Responde
`{"deleted": true, "etag"}`.

**`POST /endpoints/{file}/{name}/customize`**: mueve uno autogenerado al fichero de su tabla.
Responde su nueva ubicación, `{"file": "photos", "name": "delete"}` (con `_custom` añadido al
nombre si ya existía).

**`POST /endpoints/generate`**, con `{"tables": [...]}` (opcional; todas por defecto): como
`silence createapi`. `custom` son los que no se generan por estar personalizados; `removed`, los
ficheros `auto_` de tablas que ya no existen.

```json
{"tables": [{"table": "photos", "view": false, "generated": ["getAll", "getById", "create", "update"],
             "custom": ["delete"]}],
 "removed": []}
```

Renombrar un endpoint es `PUT` del nombre nuevo y `DELETE` del antiguo.

### Tests

**Un test**: `description`, `endpoint` (opcional, informativo) y `steps`. Cada paso, en forma
corta (`{"MÉTODO /ruta": cuerpo, "as": id, "expect": …, "save": {…}}`) o larga
(`{"request": {"method", "path", "body", "as"}, "expect", "save"}`); ver la cabecera de
`silence/testing/model.py`.

**`GET /tests`**: los tests, las versiones de los ficheros y los errores. `steps` va tal como
está en el fichero; `first` es la primera petición, ya interpretada.

```json
{"tests": [{"file": "photos", "name": "photos_only_owner_deletes", "table": "photos", "source": "custom",
            "description": "A photo of david can only be deleted by david", "endpoint": "", "composite": true,
            "first": {"method": "POST", "path": "/photos"},
            "steps": [{"POST /photos": {"user_id": 2, "title": "Test"}, "as": 2, "save": {"id": "lastId"}},
                      {"DELETE /photos/${id}": null, "as": 3, "expect": 403}]}],
 "files": {"auto_photos": "67c343e20cd053aa", "photos": "dc6da4e7e8b50d6a"},
 "errors": []}
```

**`GET`/`PUT`/`DELETE /tests/{file}/{name}`** y **`POST /tests/{file}/{name}/customize`**: como
los de los endpoints (`data` es el test).

**`POST /tests/generate`**, con `{"tables": [...]}` opcional: como `silence createtests`.
Responde `{"tables": [{"table": "photos", "tests": 14}]}`.

**`POST /tests/run`**, con `{"names": [...], "tables": [...]}` (opcionales; todos por defecto):
como `silence test`. Cada test se ejecuta en una transacción que se deshace. Por cada paso:
`status` y `response` (la respuesta de la API del alumno), y `failures` (por qué no ha pasado).
Un test se para en el primer paso que falla.

```json
{"results": [{"file": "photos", "name": "photos_without_expect_fails_on_404", "table": "photos",
              "source": "custom", "passed": false,
              "steps": [{"index": 0, "method": "GET", "path": "/photos/999", "status": 404, "passed": false,
                         "failures": ["expected a 2xx status, got 404"],
                         "response": {"code": 404, "message": "Not found"}}]}],
 "errors": []}
```

**`POST /tests/try`**, con `{"steps": [...]}`: ejecuta unos pasos sin guardarlos (también con
`ROLLBACK`). Responde `{"steps": [...]}`, con el mismo formato que los de `tests/run`.

**`POST /tests/export`**, con `{"format": "http", "tables": [...]}`: como `silence createtests
--http`. Responde `{"files": ["tests/http/photos.http"]}`.

### Estadísticas

**`GET /stats`**: las peticiones desde que arrancó el servidor (`since`, en segundos desde
1970), por grupo:

- `api`: los endpoints del alumno, agrupados por el endpoint (`GET /photos/$photo_id`), no por
  la ruta pedida; las que no encuentran endpoint, como `GET (no endpoint)`.
- `web`: los ficheros de `web/` (`/index.html`).
- `silence`: el login, el registro y el resumen de la API del alumno.

No cuentan las peticiones a esta API, al panel (`/admin/`) ni las de los tests. En cada
entrada: `count`, `errors` (estado ≥ 400), `status` (cuántas de cada código) y `avgMs`. Las
entradas van de más a menos peticiones.

```json
{"since": 1794049274.44,
 "groups": {"api": {"total": 2, "entries": [{"key": "GET /photos", "count": 1, "errors": 0, "status": {"200": 1}, "avgMs": 27.6},
                                             {"key": "GET /photos/$photo_id", "count": 1, "errors": 1, "status": {"404": 1}, "avgMs": 36.4}]},
            "web": {"total": 1, "entries": [{"key": "/index.html", "count": 1, "errors": 0, "status": {"200": 1}, "avgMs": 0.3}]},
            "silence": {"total": 0, "entries": []}}}
```

**`DELETE /stats`**: las pone a cero. Responde `{"reset": true}`.

## El panel en el proyecto

- `silence new` copia el panel en `admin/`; el servidor sirve esa carpeta en `/admin/` si
  existe, sin saber qué contiene.
- `admin/panel.json`: `{"version": "1.0.0", "api": 1}`. Al arrancar, Silence avisa si el panel
  necesita otra versión de este contrato; `silence admin update` descarga la última del repo.
