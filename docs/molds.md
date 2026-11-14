# Molds of the generated code

Silence has no code of the front-end of its own: what it generates for the front-end comes
from the molds that the project brings (from its template) in `.silence/<kind>/`. Without
them, it is not generated (and Silence says so). The template `silence-template-v3-ez-ui`
brings those of the JS API with axios, as the classes do; another template could bring them
with `fetch`.

## `js_api/`: the JS API

Silence writes it again whenever the endpoints change (when they are generated, when a file of
`endpoints/` changes, from the admin panel or by hand, and when `silence run` starts), from the
loaded endpoints: the generated ones and the custom ones, without the disabled ones. One file per
table or view, in the folder of `js_api.dir` of `silence.json`, with a function for each endpoint
of its files (`endpoints/auto_<table>.json` and `endpoints/<table>.json`: first those of the
generated endpoints, `getAll`, `getById`, `create`, `update`, `delete`, and then the custom ones,
with their names); and, with the login, `auth.js` (`login` and `logout`).

- `table.js`: the file of a table. `{{table}}` (its name, in lowercase) and `{{functions}}`
  (its functions, one after another).
- `function.js`: a function, for each endpoint of the table. `{{name}}` (of the endpoint),
  `{{description}}`, `{{method}}` (`get`, `post`, `put`, `delete`), `{{METHOD}}` (in capital
  letters), `{{route}}` (with its params as `${param}`, for a template literal), `{{params}}`
  (the params of the route and of the query string, `query_params`, separated by commas),
  `{{args}}` (the params, and `formData` first if it has a body) and `{{body}}` (`, formData` if
  it has a body; `, null` for a `POST` or `PUT` that receives no data, as `logout`). The query
  string goes in `{{route}}`, each param encoded (`?minAverage=${encodeURIComponent(minAverage)}`).
- `function_one.js` (optional): the same, for the endpoints that return one row (`getById`);
  without it, `function.js`.
- `common.js`: what the files share. `{{api_prefix}}` (`server.api_prefix`).

`table.js`, `function.js` and `common.js` are needed. Later, the molds of `silence create
view` and `silence create controller` will go next to them (`.silence/view/`,
`.silence/controller/`).
