# API de administración de Silence 3 (propuesta)

Contrato entre Silence y cualquier cliente que lo administre: el panel
(`silence-admin-panel`), la CLI, el CI o un script. Propuesta del 06/11/2026, para revisar
antes de implementarla. Sustituye a la API interna de la prueba de concepto (`/admin/api`).

## Principios

- **Prefijo `/_silence/v1`**: no choca con la API del alumno (`/api`) y lleva la versión del
  contrato. Un cambio incompatible es `/_silence/v2`; los compatibles (campos u operaciones
  nuevos) no cambian la versión.
- **Solo desde el propio ordenador** (127.0.0.1); desde otro, 403. Sin CORS: el panel se sirve
  desde el mismo origen (`/admin/`).
- **JSON** en peticiones y respuestas. Errores como en la API del alumno:
  `{"message": "...", "code": 400}`.
- **Todo en inglés**: rutas, campos y mensajes.
- **Una operación por cada acción de la CLI o del panel**, con el mismo código detrás:
  `silence createapi` es `POST /endpoints/generate`, y `silence test`, `POST /tests/run`.
- **Ficheros del proyecto como recursos**: un endpoint o un test se identifica por su fichero
  (sin `.json`) y su nombre: `/endpoints/photos/delete` es `delete` en `endpoints/photos.json`.
- **Concurrencia** (el panel y el editor a la vez): las lecturas devuelven la versión de cada
  fichero (`etag`); una escritura con `If-Match` que no coincide responde **412** y no escribe.
- **Recarga**: Silence vigila `silence.json`, `endpoints/` y `tests/`. `GET /status` incluye un
  contador `revision` que sube con cada recarga; el panel lo consulta cada pocos segundos y
  vuelve a pedir lo que ha cambiado.
- **Especificación OpenAPI** en `GET /_silence/v1/openapi.json`.

## Recursos

### Silence y el proyecto

| Operación | Respuesta |
|---|---|
| `GET /` | `{silence: "3.0.0", api: 1, project, projectDir}`: lo primero que consulta un cliente para comprobar la compatibilidad |
| `GET /status` | `revision`; `database: {name, error}`; `auth: {linked, table, …}`; número de endpoints (`auto`, `custom`) y de tests; `errors` de los ficheros (endpoints o tests que no se cargan, con fichero y motivo) |
| `GET /openapi.json` | La especificación de esta API |

### Configuración (`silence.json`)

| Operación | Cuerpo | Respuesta |
|---|---|---|
| `GET /config` | | `silence.json` sin `secret_key`, con su `etag` |
| `PATCH /config/{section}` | Los campos que cambian de `server`, `database`, `auth` o `debug` | `{restartNeeded}` (solo `server.address` y `server.port` lo necesitan). En `database`, prueba antes la conexión: si falla, 400 con el motivo y no guarda |

### Base de datos

| Operación | Cuerpo | Respuesta |
|---|---|---|
| `POST /database/test` | `{host, port, user, password, name?}` | `{ok, error}` |
| `POST /database/list` | `{host, port, user, password}` | `{databases}`: las que ve ese usuario, para elegir una |
| `GET /schema` | | Tablas y vistas: columnas (tipo, `NULL`, `DEFAULT`, `AUTO_INCREMENT`), PK, FK y UNIQUE |

### Usuarios (la tabla enlazada en `auth`)

| Operación | Cuerpo | Respuesta |
|---|---|---|
| `GET /users` | | `{pk, users: [{id, identifier, role, active, password}]}`; `password` es `argon2`, `plain` o `unsupported`, nunca su valor |
| `PUT /users/{id}/password` | `{password}` | Cifrada según `auth.password_mode` |
| `PUT /users/password` | `{password}` | La misma para todos (datos de ejemplo) |
| `POST /users/{id}/session` | | `{sessionToken, user}`: la sesión de ese usuario, sin su contraseña («Act as») |
| `POST /hash` | `{password}` | `{hash}`: como `silence hash` |

Sin tabla enlazada, 409.

### Endpoints

| Operación | Cuerpo | Respuesta |
|---|---|---|
| `GET /endpoints` | | `{endpoints: [...], files: {photos: etag, …}}`. Cada endpoint: `file`, `name`, `table`, `source` (`auto` o `custom`), su definición (`route`, `method`, `sql`, `auth_required`, `allowed_roles`, `description`, `request_body_params`, `owner`) y `warnings` |
| `GET /endpoints/{file}/{name}` | | Un endpoint |
| `PUT /endpoints/{file}/{name}` | La definición | Crea o reemplaza un endpoint personalizado. 400 si no es válido (con el motivo); 409 si su método y ruta ya están en otro sitio; en un fichero `auto_`, 400 |
| `DELETE /endpoints/{file}/{name}` | | Solo los personalizados |
| `POST /endpoints/{file}/{name}/customize` | | Lo mueve de `auto_<tabla>.json` a `<tabla>.json`; devuelve su nueva ubicación |
| `POST /endpoints/generate` | `{tables?}` | Como `silence createapi`: escribe `auto_<tabla>.json` y la API JS; devuelve lo generado y lo que no se genera por estar personalizado |

Renombrar un endpoint es `PUT` del nombre nuevo y `DELETE` del antiguo.

### Tests

| Operación | Cuerpo | Respuesta |
|---|---|---|
| `GET /tests` | | `{tests: [...], files: {…}}`. Cada test: `file`, `name`, `table`, `source`, `description` y sus `steps` |
| `GET`/`PUT`/`DELETE /tests/{file}/{name}` | El test | Como los endpoints: solo los personalizados se escriben o se borran |
| `POST /tests/{file}/{name}/customize` | | Lo mueve a `<tabla>.json` |
| `POST /tests/generate` | `{tables?}` | Como `silence createtests` |
| `POST /tests/run` | `{names?, tables?}` | Como `silence test`: `{results: [{file, name, passed, steps: [{status, failures, response}]}]}`. Cada test, en una transacción con `ROLLBACK` |
| `POST /tests/try` | `{steps}` | Ejecuta pasos sin guardarlos (al componer un test); también con `ROLLBACK` |
| `POST /tests/export` | `{format: "http", tables?}` | Como `silence createtests --http`: escribe `tests/http/<tabla>.http` y devuelve los ficheros |

### Estadísticas

| Operación | Respuesta |
|---|---|
| `GET /stats` | Desde que arrancó Silence: peticiones por grupo (`silence`, `api`, `web`) y por ruta, con códigos de estado, errores y tiempo medio. No cuentan las de esta API ni las de los tests |
| `DELETE /stats` | Las pone a cero |

## El panel en el proyecto

- `silence new` copia el panel en `admin/`; Silence sirve esa carpeta en `/admin/` si existe,
  sin saber qué contiene.
- `admin/panel.json`: `{"version": "1.0.0", "api": 1}`. Al arrancar, Silence avisa si el panel
  necesita otra versión de la API; `silence admin update` descarga la última del repo.

## Cambios respecto a la prueba de concepto

| Prueba de concepto (`/admin/api`) | Contrato (`/_silence/v1`) |
|---|---|
| `PUT /config/{section}` | `PATCH /config/{section}` |
| `POST /db/test`, `POST /db/databases` | `POST /database/test`, `POST /database/list` |
| `PUT /users/passwords` | `PUT /users/password` |
| `POST /users/{id}/token` | `POST /users/{id}/session` |
| `PUT`/`DELETE /endpoints/custom` con `{file, name}` en el cuerpo | `PUT`/`DELETE /endpoints/{file}/{name}` |
| `POST /endpoints/customize` con `{method, route}` | `POST /endpoints/{file}/{name}/customize` |
| Lo mismo para los tests | Ídem |
| — | `GET /`, `revision`, `etag`/`If-Match`, `POST /hash`, `POST /tests/export`, `GET /openapi.json` |
