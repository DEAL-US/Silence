# Molds of the generated code

Silence has no code of the front-end of its own: what it generates for the front-end comes
from the molds that the project brings (from its template) in `.silence/<kind>/`. Without
them, it is not generated (and Silence says so). The template `silence-template-v3-ez-ui`
brings those of the JS API with axios, as the classes do; another template could bring them
with `fetch`.

## `js_api/`: the JS API (`silence createapi`, or generating the endpoints)

One file per table or view, in the folder of `js_api.dir` of `silence.json`:

- `table.js`: the file of a table. `{{table}}` (its name, in lowercase) and `{{functions}}`
  (its functions, one after another).
- `function.js`: a function, for each endpoint of the table. `{{name}}` (of the endpoint),
  `{{description}}`, `{{method}}` (`get`, `post`, `put`, `delete`), `{{METHOD}}` (in capital
  letters), `{{route}}` (with its params as `${param}`, for a template literal), `{{params}}`
  (the params of the route, separated by commas), `{{args}}` (the params, and `formData` first
  if it has a body) and `{{body}}` (`, formData` if it has a body).
- `function_one.js` (optional): the same, for the endpoints that return one row (`getById`);
  without it, `function.js`.
- `common.js`: what the files share. `{{api_prefix}}` (`server.api_prefix`).

`table.js`, `function.js` and `common.js` are needed. Later, the molds of `silence create
view` and `silence create controller` will go next to them (`.silence/view/`,
`.silence/controller/`).
