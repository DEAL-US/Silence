// Database: the connection (tested before saving it) and the users table.
import { api, esc, attempt, toast } from "../ui.js";

export async function render(main, app) {
  const config = await api("/config");
  const db = config.database;
  const auth = config.auth;

  main.innerHTML = `
    <h1>Database</h1>
    <section class="sa-section">
      <h2>Connection</h2>
      <p class="sa-muted">Silence uses an existing database: create it and load its data first
        (for example, with the scripts of the project's <code>sql/</code> folder).</p>
      <form class="sa-form" id="db-form">
        <div class="ez-field"><label for="db-host">Host</label><input id="db-host" name="host" value="${esc(db.host)}" required></div>
        <div class="ez-field"><label for="db-port">Port</label><input id="db-port" name="port" type="number" value="${esc(db.port)}" required></div>
        <div class="ez-field"><label for="db-user">User</label><input id="db-user" name="user" value="${esc(db.user)}" required></div>
        <div class="ez-field"><label for="db-password">Password</label><input id="db-password" name="password" type="password" value="${esc(db.password)}"></div>
        <div class="ez-field"><label for="db-name">Database</label>
          <select id="db-name" name="name"><option value="${esc(db.name)}">${esc(db.name || "(choose one)")}</option></select></div>
        <div class="sa-toolbar">
          <button class="ez-button ez-button--secondary" type="button" id="db-list">Load the databases</button>
          <button class="ez-button" type="submit">Test and save</button>
        </div>
      </form>
      <p id="db-result"></p>
    </section>

    <section class="sa-section" id="auth-section">
      <h2>Users table</h2>
      <p class="sa-muted">The table with the users of your application: it enables <code>POST ${esc(app.status.apiPrefix)}/login</code>
        and <code>/register</code>, sessions, roles (a column of the table) and owners.</p>
      <div id="auth-body"></div>
    </section>`;

  const form = main.querySelector("#db-form");
  const values = () => Object.fromEntries(new FormData(form));

  main.querySelector("#db-list").addEventListener("click", async () => {
    const res = await attempt(() => api("/db/databases", "POST", values()));
    if (!res) return;
    if (!res.ok) {
      toast(res.error, "error");
      return;
    }
    const select = main.querySelector("#db-name");
    const selected = select.value;
    select.innerHTML = `<option value="">(choose one)</option>` + res.databases.map((d) =>
      `<option ${d === selected ? "selected" : ""}>${esc(d)}</option>`).join("");
    toast(`${res.databases.length} databases`, "success");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const v = values();
    v.port = Number(v.port);
    const res = await attempt(() => api("/config/database", "PUT", v), "Connected and saved in silence.json");
    if (res) {
      await app.refreshStatus();
      renderAuth(main, app);
    }
  });

  renderAuth(main, app, auth);
}

async function renderAuth(main, app) {
  const body = main.querySelector("#auth-body");
  if (app.status.database.error) {
    body.innerHTML = `<div class="ez-alert ez-alert--warning">Connect to the database first.</div>`;
    return;
  }
  const config = await api("/config");
  const auth = config.auth;
  const schema = await api("/schema");
  const tables = schema.relations.filter((r) => !r.view);

  const options = (cols, selected, empty) => `<option value="">${empty}</option>` +
    cols.map((c) => `<option ${c === selected ? "selected" : ""}>${esc(c)}</option>`).join("");

  body.innerHTML = `
    <form class="sa-form" id="auth-form">
      <div class="ez-field"><label for="auth-table">Table</label>
        <select id="auth-table" name="table">${options(tables.map((t) => t.name), auth.table, "(not linked)")}</select></div>
      <div class="ez-field"><label for="auth-identifier">Identifier</label><select id="auth-identifier" name="identifier"></select></div>
      <div class="ez-field"><label for="auth-password">Password</label><select id="auth-password" name="password"></select></div>
      <div class="ez-field"><label for="auth-role">Role (optional)</label><select id="auth-role" name="role"></select></div>
      <div class="ez-field"><label for="auth-active">Active (optional)</label><select id="auth-active" name="active"></select></div>
      <div class="ez-field"><label for="auth-mode">Passwords</label>
        <select id="auth-mode" name="password_mode">
          <option value="argon2" ${auth.password_mode === "argon2" ? "selected" : ""}>Encrypted (argon2)</option>
          <option value="plain" ${auth.password_mode === "plain" ? "selected" : ""}>Plain text</option>
        </select></div>
      <div class="ez-field"><label for="auth-default-role">Role of new users (register)</label>
        <input id="auth-default-role" name="default_role" value="${esc(auth.default_role)}"></div>
      <div class="ez-field"><label><input type="checkbox" name="login" ${auth.login ? "checked" : ""}> Login</label>
        <label><input type="checkbox" name="register" ${auth.register ? "checked" : ""}> Register</label></div>
      <div class="sa-toolbar"><button class="ez-button" type="submit">Save</button></div>
    </form>`;

  const form = body.querySelector("#auth-form");
  const tableSelect = form.querySelector("#auth-table");
  const fillColumns = () => {
    const table = tables.find((t) => t.name === tableSelect.value);
    const cols = table ? table.columns.map((c) => c.name) : [];
    const guess = (names) => cols.find((c) => names.includes(c.toLowerCase())) ?? "";
    const pick = (field, names) => (table && table.name === auth.table && auth[field]) ? auth[field] : guess(names);
    form.querySelector("#auth-identifier").innerHTML = options(cols, pick("identifier", ["email", "username", "login"]), "—");
    form.querySelector("#auth-password").innerHTML = options(cols, pick("password", ["password", "pass", "pwd"]), "—");
    form.querySelector("#auth-role").innerHTML = options(cols, pick("role", ["role", "rol", "position", "type"]), "(none)");
    form.querySelector("#auth-active").innerHTML = options(cols, pick("active", ["active", "isactive", "is_active", "enabled"]), "(none)");
  };
  tableSelect.addEventListener("change", fillColumns);
  fillColumns();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const v = Object.fromEntries(new FormData(form));
    v.login = form.querySelector("[name=login]").checked;
    v.register = form.querySelector("[name=register]").checked;
    if (v.table && (!v.identifier || !v.password)) {
      toast("Choose the identifier and password columns", "error");
      return;
    }
    if (!v.table) {
      v.identifier = v.password = v.role = v.active = "";
    }
    if (await attempt(() => api("/config/auth", "PUT", v), "Saved in silence.json")) {
      await app.refreshStatus();
    }
  });
}
