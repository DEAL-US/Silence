// Users: the rows of the linked users table, their passwords and "act as".
import { api, esc, attempt, dialog, session, toast } from "../ui.js";

const STATUS = {
  argon2: `<span class="ez-badge ez-badge--success">argon2</span>`,
  plain: `<span class="ez-badge">plain text</span>`,
  unsupported: `<span class="ez-badge ez-badge--danger">unsupported hash</span>`,
};

export async function render(main, app) {
  main.innerHTML = `<h1>Users</h1><div id="users-body"></div>`;
  const body = main.querySelector("#users-body");
  if (!app.status.auth.linked) {
    body.innerHTML = `<div class="ez-alert ez-alert--warning">Link the users table first, in <a href="#/database">Database</a>.</div>`;
    return;
  }

  const load = async () => {
    const res = await attempt(() => api("/users"));
    if (!res) return;
    const mode = res.passwordMode;
    const wrong = res.users.filter((u) => u.password === "unsupported" || (mode === "argon2" && u.password === "plain"));
    body.innerHTML = `
      ${wrong.length ? `<div class="ez-alert ez-alert--warning">${wrong.length} users cannot log in: their stored password is
        ${mode === "argon2" ? "not an argon2 hash" : "a hash that Silence does not support"}. Set their password again.</div>` : ""}
      <div class="sa-toolbar">
        <span class="sa-muted">Passwords are stored ${mode === "argon2" ? "encrypted (argon2)" : "as plain text"}.</span>
        <span class="sa-toolbar__spacer"></span>
        <button class="ez-button ez-button--secondary" type="button" id="all-passwords">Same password for everybody</button>
      </div>
      <div class="ez-scroll"><table class="sa-table">
        <thead><tr><th>${esc(res.pk)}</th><th>${esc(app.status.auth.identifier)}</th>
          ${app.status.auth.role ? `<th>${esc(app.status.auth.role)}</th>` : ""}
          ${app.status.auth.active ? `<th>${esc(app.status.auth.active)}</th>` : ""}
          <th>Password</th><th></th></tr></thead>
        <tbody>${res.users.map((u) => `
          <tr>
            <td>${esc(u.id)}</td><td>${esc(u.identifier)}</td>
            ${app.status.auth.role ? `<td>${esc(u.role ?? "—")}</td>` : ""}
            ${app.status.auth.active ? `<td>${u.active ? "yes" : "no"}</td>` : ""}
            <td>${STATUS[u.password]}</td>
            <td class="sa-actions">
              <button class="ez-button ez-button--secondary sa-button--small" data-password="${esc(u.id)}" type="button">Set password</button>
              <button class="ez-button sa-button--small" data-act="${esc(u.id)}" data-label="${esc(u.identifier)}" type="button">Act as</button>
            </td>
          </tr>`).join("")}</tbody>
      </table></div>
      <p class="sa-muted sa-small">«Act as» opens a session for that user without its password: the endpoints that you
        try in this panel are sent with its token.</p>`;

    body.querySelector("#all-passwords").addEventListener("click", async () => {
      const v = await dialog("Same password for everybody", passwordField(), "Save");
      if (v && await attempt(() => api("/users/passwords", "PUT", v), "Passwords saved")) {
        load();
      }
    });
    for (const button of body.querySelectorAll("[data-password]")) {
      button.addEventListener("click", async () => {
        const v = await dialog(`Password of user ${button.dataset.password}`, passwordField(), "Save");
        if (v && await attempt(() => api(`/users/${encodeURIComponent(button.dataset.password)}/password`, "PUT", v), "Password saved")) {
          load();
        }
      });
    }
    for (const button of body.querySelectorAll("[data-act]")) {
      button.addEventListener("click", async () => {
        const res = await attempt(() => api(`/users/${encodeURIComponent(button.dataset.act)}/token`, "POST"));
        if (res) {
          session.set({ token: res.sessionToken, label: button.dataset.label });
          toast(`Acting as ${button.dataset.label}`, "success");
        }
      });
    }
  };
  load();
}

function passwordField() {
  return `<div class="ez-field"><label for="new-password">New password</label>
    <input id="new-password" name="password" required autocomplete="new-password"></div>`;
}
