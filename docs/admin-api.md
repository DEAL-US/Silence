# API de administración de Silence 3

Contrato entre Silence y cualquier cliente que lo administre: el panel
(`silence-v3-admin-panel-uikit`), la CLI, el CI o un script. Aprobado el 06/11/2026 y completado con los
formatos el 07/11/2026; simplificado el 08/11/2026 (de 26 operaciones a 15: los ficheros del
proyecto con una sola API, y las estadísticas en el panel, con el registro de peticiones). Es la única pieza que comparten Silence y el panel: otro backend (por
ejemplo, Silence de Rust) que lo cumpla sirve con el mismo panel. `tests/ci_project/test/
test_admin_api.py` comprueba que una URL lo cumple.

## Principios

- **Prefijo `/_silence/v1`**: no choca con la API del alumno (`/api`) y lleva la versión del
  contrato. Un cambio incompatible es `/_silence/v2`; los compatibles (campos u operaciones
  nuevos) no cambian la versión. Los clientes ignoran los campos que no conocen.
- **Solo desde el propio ordenador** (127.0.0.1); desde otro, 403. Sin CORS: el panel se sirve
  desde el mismo origen (`/admin/`). Además, la cabecera `Host` tiene que ser `localhost`,
  `127.0.0.1` o `[::1]` (una página de otro sitio cuyo nombre apunte a 127.0.0.1, *DNS rebinding*,
  recibe 403), y un `POST`, `PUT` o `DELETE` con un `Origin` que no sea el propio también (un
  formulario de otra web que envíe aquí, CSRF).
- **JSON** en peticiones y respuestas; UTF-8; nombres de campos en camelCase, salvo los de la
  definición de un endpoint, que son los de su fichero (`auth_required`…).
- **Todo en inglés**: rutas, campos y mensajes.
- **Solo lo que solo puede hacer el servidor**: lo que necesita la conexión con MariaDB, la
  `secret_key` o argon2. El resto lo hace el cliente: leer, cambiar y escribir los ficheros del
  proyecto, ejecutar los tests y resumir el registro de peticiones. Las órdenes de la CLI y de la
  API comparten código: `silence createapi` es `POST /endpoints/generate`, y `silence createdb`,
  `POST /database/reload`.
- **Silence no ejecuta tests**: genera los que se deducen de los endpoints (al pedirlos, sin
  guardarlos) y guarda los propios; los ejecuta el panel contra la API del alumno, sin
  transacciones: cambian la BD.
- **Los ficheros del proyecto, con una sola API** (`/files/{ruta}`): `silence.json`,
  `endpoints/*.json`, `tests/*.json` y el registro de peticiones (`admin/logs/requests.log`). Se leen y se escriben enteros; Silence valida cada uno
  según lo que es antes de guardarlo. Los ficheros `endpoints/auto_<tabla>` los genera Silence (solo
  se leen); los demás son del usuario. Los tests generados no son ficheros.
- **Concurrencia**: las lecturas devuelven la versión de cada fichero (`etag`, un texto opaco;
  `""` si el fichero no existe). Una escritura con la cabecera `If-Match` que no coincide responde
  **412** y no escribe; sin `If-Match`, escribe siempre.
- **Recarga**: el servidor vigila `silence.json`, `endpoints/` y `tests/`, y los recarga cuando
  cambian, los cambie quien los cambie (el panel no consulta el estado periódicamente: lo lee al
  cambiar de página y tras cada acción).
- **Especificación OpenAPI** en `GET /_silence/v1/openapi.json`, con los esquemas de las
  respuestas.

## Errores

Cualquier error responde `{"message": "...", "code": N}` (el mismo formato que la API del
alumno), con estos códigos:

| Código | Cuándo |
|---|---|
| 400 | La petición no es válida (el motivo va en `message`): un valor de `silence.json` incorrecto o una conexión que no funciona, un endpoint o un test mal definido, un nombre no válido, un JSON mal formado |
| 403 | La petición no viene del propio ordenador (o de una página suya); o un fichero que no se puede tocar: fuera de los de la API de ficheros, un `auto_` (escribirlo o borrarlo), escribir el registro, borrar `silence.json` |
| 404 | El recurso no existe (un usuario, un fichero que se borra) |
| 409 | El estado no lo permite: la BD no está configurada o no responde, la tabla de usuarios no está enlazada, un endpoint con el método y la ruta de otro **personalizado** (o dos veces en el mismo fichero), un test con el nombre de uno generado o de uno de otro fichero |
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
versión de este contrato). `versions` da la versión de cada pieza: Silence, el panel (el de
`silence.json` y el instalado en `admin/`, con la versión de esta API que necesita), la plantilla
del front-end (la que apuntó `silence new`) y ez-ui (`web/ez-ui/VERSION.txt`); `null` si el
proyecto no la tiene o no se sabe. Con **`?updates=true`** añade `latest`, la última versión
publicada de cada una (PyPI para Silence; las etiquetas de su repo, o de su copia local con
`SILENCE_SOURCES`, para las demás; `GITHUB_TOKEN` si el repo es privado), o por qué no se sabe.
Va a la red: solo cuando se pide.

```json
{"silence": "3.0.0", "api": 1, "project": "galeria", "projectDir": "/home/student/galeria",
 "versions": {"silence": {"version": "3.0.0.dev0", "adminApi": 1},
              "panel": {"repo": "DEAL-US/silence-v3-admin-panel-uikit", "version": "v1.1.0", "installed": "1.1.0", "adminApi": 1},
              "template": {"repo": "DEAL-US/silence-template-v3-ez-ui", "version": "v1.1.1"},
              "ezUi": {"repo": "IISSI-US/ez-ui", "version": "1.0.1"}},
 "latest": {"silence": {"version": "2.2.0"}, "panel": {"version": "v1.0.0"},
            "template": {"version": "v1.1.1"}, "ezUi": {"error": "Cannot read the versions of IISSI-US/ez-ui (HTTP 404; if it is private, set GITHUB_TOKEN)"}},
 "studentApi": {"prefix": "/api", "sessionHeader": "Token"}}
```

**`GET /status`**: el estado del proyecto. `database.error` es `null` si hay conexión; `auth`
lleva `linked` y los valores de `auth` de `silence.json`; `endpoints.list`, los endpoints que se
están sirviendo (ver «Endpoints»); `jsApi`, la carpeta de la API JS y, si no se genera, por qué
(está desactivada o el proyecto no tiene sus moldes); `errors` son los problemas de los ficheros,
como texto.

```json
{"apiPrefix": "/api", "baseUrl": "http://127.0.0.1:8080",
 "database": {"name": "silence_gallery_db", "error": null},
 "auth": {"linked": true, "table": "users", "identifier": "email", "password": "password",
          "role": "", "active": "", "password_mode": "argon2", "login": true, "token_max_age": 86400},
 "endpoints": {"count": 40, "auto": 39, "custom": 1, "list": [ … ]},
 "tests": {"custom": 2},
 "jsApi": {"dir": "web/js/api/_auto", "notGenerated": null},
 "errors": {"config": [], "endpoints": [], "tests": []}}
```

**`GET /openapi.json`**: la especificación de esta API.

### Ficheros del proyecto

| Ruta | Qué es | Se puede |
|---|---|---|
| `silence.json` | La configuración | leer y escribir |
| `endpoints/<nombre>.json` | Endpoints (por nombre); `auto_<tabla>`, los generados | leer y escribir (los `auto_`, solo leer) |
| `tests/<nombre>.json` | Tests propios (por nombre) | leer, escribir y borrar |
| `admin/logs/requests.log` | El registro de peticiones (texto) | leer y borrar |
| `<js_api.dir>/<tabla>.js` | La API JS generada (texto) | solo leer |
| `.silence/js_api/<molde>.js` | Los moldes de la API JS, de la plantilla (texto; ver `docs/molds.md`) | solo leer |

Los nombres, de letras, dígitos, `_` y `-`. Cualquier otra ruta, 403.

**`GET /files`** (o **`GET /files?dir=endpoints`**, con `endpoints`, `tests` o
`admin/logs`): los ficheros que hay, con su versión.

```json
{"files": [{"path": "silence.json", "etag": "f9a1870f02a230d0"},
           {"path": "endpoints/auto_photos.json", "etag": "0406d02937a18b55"},
           {"path": "endpoints/photos.json", "etag": "96b41b2f1b5e8b1a"}]}
```

**`GET /files/{ruta}`**: el contenido y su versión. `data` es el JSON del fichero (el registro,
su texto), o `null` si no existe (con `etag` `""`).

```json
{"path": "endpoints/photos.json", "etag": "96b41b2f1b5e8b1a",
 "data": {"delete": {"route": "/photos/$photo_id", "method": "DELETE",
                     "sql": "DELETE FROM photos WHERE photo_id = $photo_id", "auth_required": true,
                     "owner": "user_id", "description": "Deletes a photo (only its owner)"}}}
```

`silence.json` se devuelve sin `secret_key` y con los valores por defecto de lo que falte:

```json
{"path": "silence.json", "etag": "f9a1870f02a230d0",
 "data": {"version": 3,
          "server": {"address": "127.0.0.1", "port": 8080, "api_prefix": "/api", "open_browser": true,
                     "log_bodies": true, "decimals_as_strings": false, "check_updates": true},
          "database": {"host": "127.0.0.1", "port": 3306, "user": "iissi_user", "password": "iissi$user",
                       "name": "silence_gallery_db", "scripts": ["create_tables.sql", "populate.sql"]},
          "auth": {"table": "users", "identifier": "email", "password": "password", "role": "",
                   "active": "", "password_mode": "argon2", "login": true, "token_max_age": 86400},
          "js_api": {"enabled": true, "dir": "web/js/api/_auto"},
          "admin": {"repo": "DEAL-US/silence-v3-admin-panel-uikit", "version": "v1.1.0"},
          "debug": false}}
```

**`PUT /files/{ruta}`**, con el contenido entero como cuerpo (y `If-Match` con la versión que se
leyó): lo valida y lo guarda. Responde `{"path", "etag"}`, con 201 si el fichero es nuevo.

- `silence.json`: sin claves desconocidas y con valores válidos; si cambia la conexión, la prueba
  antes de guardar; los scripts de `database.scripts` deben estar en `sql/`. Se conserva su
  `secret_key` (si el cuerpo trae una, se ignora). La respuesta añade `restartNeeded`, `true` solo
  si cambian `server.address` o `server.port`.
- `endpoints/<nombre>.json`: cada endpoint bien definido (400), sin el método y la ruta de otro
  personalizado de otro fichero ni repetidos en el mismo (409). Uno con el método y la ruta de uno
  autogenerado lo sustituye: así se personaliza un endpoint generado (y al borrar el propio, vuelve
  el generado). Silence recarga los endpoints al guardarlo.
- `tests/<nombre>.json`: cada test unitario bien definido (400; ver «Tests»), sin el nombre de
  uno generado ni de uno de otro fichero (409).

Un fichero vacío (`{}`) en `endpoints/` o en `tests/` vale; para quitarlo, `DELETE`.

**`DELETE /files/{ruta}`** (con `If-Match`, si se quiere): lo borra y responde
`{"deleted": true}`; 404 si no existe. Borrar el registro de peticiones pone a cero la actividad y
las estadísticas del panel (Logs).

Cambiar una entrada (un endpoint, un test) es leer su fichero, cambiarla y escribirlo; renombrarla,
lo mismo con su nombre nuevo. Para moverla a otro fichero, se quita del antiguo y se añade al
nuevo (si no, el nuevo choca con el antiguo: 409).

### Base de datos

**`POST /database/test`**, con `{"host", "port", "user", "password", "name"}` (`name`
opcional): prueba una conexión sin guardarla y, si el usuario puede conectarse, dice qué BD ve.

```json
{"ok": true, "error": null, "databases": ["animals_db", "gallery_db", "silence_gallery_db"]}
```

(con un error de conexión: `{"ok": false, "error": "Access denied for user …", "databases": []}`;
con una BD que no existe, `ok` es `false` pero `databases` trae las que ve)

**`POST /database/reload`**: crea de nuevo la BD con los scripts de `sql/` que lista
`database.scripts` de `silence.json`, en ese orden, como `silence createdb` (y como
`SQL_SCRIPTS` en Silence 2): `DROP DATABASE`, `CREATE DATABASE` y cada script tras un `USE`,
con `DELIMITER` para los procedimientos y triggers. Sirve, por ejemplo, para volver a ejecutar
los tests desde los datos originales.

```json
{"scripts": [{"file": "create_tables.sql", "statements": 4}, {"file": "populate.sql", "statements": 2}]}
```

Si un script falla, 400 con dónde: `{"code": 400, "message": "populate.sql, line 12: …",
"file": "populate.sql", "line": 12, "statement": "INSERT INTO …"}` (los anteriores ya se han
ejecutado). Sin scripts en `database.scripts`, 409.

Al guardar `silence.json` se comprueba que los scripts existen en `sql/` (si no, 400 y no guarda
nada); los que falten después (un script borrado, `silence.json` editado a mano) salen en los
errores de configuración de `GET /status`.

**`GET /schema`**: tablas y vistas de la BD, con su número de filas (`rows`; `null` si no se
puede contar, por ejemplo una vista que ya no funciona).

```json
{"database": "silence_gallery_db",
 "relations": [{"name": "comments", "view": false, "pk": ["comment_id"], "rows": 12,
                "fks": [{"column": "user_id", "refTable": "users", "refColumn": "user_id"}],
                "uniques": [],
                "columns": [{"name": "comment_id", "type": "int(11)", "nullable": false, "default": null,
                             "autoIncrement": true, "generated": false, "optional": true}]}]}
```

`optional` dice si un `INSERT` puede omitir la columna (admite `NULL`, tiene `DEFAULT`, es
`AUTO_INCREMENT` o calculada); `uniques` son los índices UNIQUE (listas de columnas).

### Usuarios (la tabla enlazada en `auth`)

Sin tabla enlazada, todas responden 409.

El identificador (`auth.identifier`) es una columna de la tabla de usuarios (`email`) o de una
tabla a la que esta apunta con una clave ajena (`people.email`, cuando las credenciales están en
su propia tabla: `credentials(person_id → people, password, role)`). En el segundo caso Silence
lee los usuarios con un `JOIN` por esa clave ajena y el login recibe `email`.

**`GET /users`**: los usuarios, con el estado de su contraseña (`argon2`, `plain` o
`unsupported`). Su valor (`plainPassword`) solo si está en texto plano y el proyecto guarda así
las contraseñas (`auth.password_mode: plain`, para las BD de prácticas): sirve para probar el
login. `role` y `active` son `null` si no hay esas columnas.

```json
{"pk": "user_id", "passwordMode": "argon2",
 "users": [{"id": 1, "identifier": "agu@gallery.com", "role": null, "active": null, "password": "argon2",
            "plainPassword": null}]}
```

**`PUT /users/{id}/password`**, con `{"password": "…"}`: la guarda cifrada o no, según
`auth.password_mode`. Responde `{"updated": 1}`.

**`POST /users/{id}/session`**: la sesión de ese usuario, sin su contraseña, para usarla con la
API del alumno; `user` es su fila sin la contraseña.

```json
{"sessionToken": ".eJxNzU0KAjEMhuGrDF3L…", "user": {"user_id": 2, "email": "david@gallery.com", "username": "druiz"}}
```

### Endpoints

**Definición de un endpoint** (la de su fichero): `route` (con `$param`), `method` (`GET`,
`POST`, `PUT` o `DELETE`), `sql` (con `$param` y `$loggedId`), `auth_required`,
`allowed_roles` (`["*"]`: cualquier usuario con sesión; unos roles concretos implican la sesión),
`description`, `request_body_params`
(los del cuerpo), `query_params` (los de la *query string* que usa el SQL, los filtros de una
colección: `?minAverage=7` → `$minAverage`; si falta uno, 400), `owner` (la columna con el id del
usuario dueño de cada fila, o `null`: cada usuario con sesión actúa solo sobre sus filas, también al
leer, y los roles de `allowed_roles`, si los hay, sobre todas) y `disabled` (solo en uno propio: `true`, no se publica). El resto de la *query string* filtra y ordena el resultado de un `GET` (`?columna=valor`,
`_sort`, `_order`, `_limit`, `_page`).

**Los endpoints** están en `endpoints.list` de `GET /status`: los generados y los propios, con su
fichero y nombre, y también los desactivados (`"disabled": true`), que no se sirven. `endpoints.count`
cuenta los que se sirven y `endpoints.disabled`, los desactivados.

```json
[{"file": "photos", "name": "delete", "table": "photos", "source": "custom",
  "route": "/photos/$photo_id", "fullRoute": "/api/photos/$photo_id", "method": "DELETE",
  "sql": "DELETE FROM photos WHERE photo_id = $photo_id", "auth_required": true,
  "allowed_roles": ["*"], "description": "Deletes a photo (only its owner)",
  "request_body_params": [], "owner": "user_id",
  "overrides": ["auto_photos.json"], "warnings": [], "disabled": false}]
```

`source` es `auto` (fichero `auto_<tabla>`) o `custom`; `overrides`, los ficheros autogenerados
cuyo endpoint (el mismo método y ruta) sustituye este; `warnings`, avisos que no impiden cargarlo.
Los errores de los ficheros (lo que no se ha podido cargar) están en `errors.endpoints`.

Los endpoints se leen y se escriben con la API de ficheros (`endpoints/<nombre>.json`).
Personalizar uno generado es escribir en el fichero propio de su tabla uno con su método y ruta:
el propio lo sustituye. **Desactivarlo** (que no se publique) es lo mismo, con `"disabled": true`:
no se sirve (404, o 405 si la ruta tiene otros métodos), ni sale en el resumen de la API, ni en la
API JS, ni en los tests generados; el generado sigue en su fichero, y vuelve al borrar la copia.

**`POST /endpoints/generate`**, con `{"tables": [...]}` (opcional; todas por defecto): como
`silence createapi`. `custom` son los que no se generan por estar personalizados; `removed`, los
ficheros `auto_` de tablas que ya no existen. Todos son públicos (la sesión, los roles y el propietario se
ponen al personalizarlos), también los de la tabla de usuarios enlazada, que es una tabla más:
en modo argon2, sus lecturas no envían las contraseñas y sus escrituras las cifran; en modo `plain`
(bases de datos de prácticas), las contraseñas se guardan y se ven tal cual. Un endpoint
público que cambia la tabla de usuarios lleva un aviso (cualquiera podría cambiar usuarios, roles
y contraseñas): el alumno le pone sesión y roles.

Con los endpoints se genera la API JS (`js_api.dir`), rellenando los moldes que trae el proyecto
de su plantilla (`.silence/js_api/`; ver `docs/molds.md`): Silence no tiene código del front-end
propio. Sin moldes (o con `js_api.enabled` a `false`), no se genera, y `jsApi.notGenerated` dice
por qué.

```json
{"tables": [{"table": "photos", "view": false, "generated": ["getAll", "getById", "create", "update"],
             "custom": ["delete"]}],
 "removed": [], "jsApi": {"dir": "web/js/api/_auto", "notGenerated": null}}
```

### Tests

**Un test** es siempre **unitario**: una petición y lo que se espera (un código de estado y,
si acaso, un fragmento del mensaje de error), en forma corta (`{"MÉTODO /ruta": cuerpo, "as":
id, "expect": 403}` o `"expect": {"status": 400, "message": "validSalary"}`) o larga
(`{"request": {"method", "path", "body", "as"}, "expect"}`); ver la cabecera de
`silence/testing/model.py`. Hay dos clases:

- **generados** (`source: auto`): Silence los deduce de los endpoints y de los datos cada vez que
  se piden; no se guardan ni se editan, así que siempre siguen a los endpoints. `file` es el de
  su tabla.
- **propios** (`source: custom`): `tests/<tabla>.json`, del alumno (por ejemplo, para las reglas
  de negocio), que se leen y se escriben con la API de ficheros. No pueden llamarse como un
  generado: la API de ficheros no lo guarda (409; sin BD, tampoco, porque no lo puede comprobar).
  Si alguien lo escribe a mano en el fichero, vale el generado y el panel no usa el propio.

Un test es una sola petición: no hay secuencias de tests. Un fichero `tests/auto_*.json` de una
versión anterior no se carga: sale como error.

**`GET /tests/generated`**: los tests generados, calculados en ese momento con los endpoints y los
datos de la BD (para que los positivos usen valores que existen y los negativos, valores que no
chocan); sin BD, 409. `definition` va en forma corta, como se escribiría en un fichero; `request`
y `expect`, ya interpretados.

```json
{"tests": [{"file": "departments", "name": "departments_getById_not_found", "table": "departments",
            "source": "auto", "description": "GET /departments/$departmentId: a row that does not exist is a 404",
            "endpoint": "GET /departments/$departmentId",
            "definition": {"GET /departments/999999999": null, "expect": 404, "description": "…", "endpoint": "…"},
            "request": {"method": "GET", "path": "/departments/999999999", "body": null, "as": null},
            "expect": {"status": 404}}]}
```

Un test con `steps` (varias peticiones) o con otra cosa esperada que no sea `status` y `message`
no es válido (400 al guardarlo).

Silence no ejecuta los tests: no hay `tests/run`, `tests/try` ni `silence test`. Tampoco se
generan, personalizan ni exportan ficheros (`tests/generate`, `…/customize`, `tests/export` y
`silence createtests` ya no existen). El panel los ejecuta contra la API del alumno en el orden
`GET`, `POST`, `PUT`, `DELETE`, abriendo la sesión de cada `as` con `POST /users/{id}/session`.

### Registro de peticiones

Silence escribe en `admin/logs/requests.log` una línea por cada petición a la aplicación del
alumno, como el registro de accesos de cualquier servidor web; el panel lo muestra en Logs (su
actividad) y lo resume en sus estadísticas. No se apuntan las del panel (`/admin/` y esta API). Se guardan
las últimas 10 000 líneas; si se borra, Silence lo crea de nuevo con la siguiente. `silence new`
lo pone en el `.gitignore`.

```text
2026-11-08T08:01:12 api GET /api/employees/3 200 4ms 312B /employees/$employeeId
2026-11-08T08:01:13 silence POST /api/login 400 9ms 60B /login The user or the password are not correct
2026-11-08T08:01:14 web GET /css/main.css 404 1ms 0B - Not found
```

Campos, separados por un espacio: la hora (local), el grupo, el método, la ruta pedida (con su
*query string*, codificada), el código de estado, el tiempo, los bytes enviados, la ruta del
endpoint que respondió (`-` si ninguno) y, en los errores, el mensaje (hasta el final de la
línea). Los grupos, como en Silence de Rust:

- `api`: la API del alumno (sus endpoints); las que no encuentran endpoint llevan `-`.
- `silence`: lo que Silence da a la aplicación del alumno: el login, el logout y el resumen
  (`GET /api`).
- `web`: los ficheros de `web/` (la aplicación del alumno).

## El panel en el proyecto

- `silence new` copia el panel en `admin/`; el servidor sirve esa carpeta en `/admin/` si
  existe, sin saber qué contiene.
- `admin/panel.json`: `{"version": "1.0.0", "api": 1}`. Al arrancar, Silence avisa si el panel
  necesita otra versión de este contrato.
- `silence.json` anota qué panel tiene el proyecto (`"admin": {"repo", "version"}`, o `null`);
  `silence admin update` instala ese (o el del índice de Silence, `templates.json`) y
  `--version`, `--latest` o `--repo` lo cambian. Se lee con `GET /files/silence.json`; aunque se
  puede escribir, cambiarlo no instala nada: es cosa de la CLI, que es la que instala el panel.
