// Helpers shared by the pages of the admin panel.
import { ezToast } from "../ez-ui/js/toast.js";
import { ezConfirm } from "../ez-ui/js/dialog.js";

/** Calls the admin API (/admin/api) and returns its JSON, or throws an Error with its message. */
export async function api(path, method = "GET", body = undefined) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch("/admin/api" + path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || `Error ${response.status}`);
  }
  return data;
}

/** Escapes a value to put it in HTML. */
export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

export function toast(message, type = "info") {
  ezToast(message, type, type === "error" ? 8000 : 4000);
}

/** Runs an async action showing its error (if any) in a toast. */
export async function attempt(action, success) {
  try {
    const res = await action();
    if (success) {
      toast(success, "success");
    }
    return res;
  } catch (error) {
    toast(error.message, "error");
    return undefined;
  }
}

/** Opens the dialog with some HTML; resolves to the form's values, or null if cancelled. */
export async function dialog(title, html, okText = "OK") {
  const dlg = document.querySelector("#dialog");
  dlg.querySelector("#dialog-title").textContent = title;
  dlg.querySelector("#dialog-body").innerHTML = html;
  dlg.querySelector("#dialog-ok").textContent = okText;
  const confirmed = await ezConfirm(dlg);
  if (!confirmed) {
    return null;
  }
  const values = {};
  for (const field of dlg.querySelectorAll("[name]")) {
    values[field.name] = field.type === "checkbox" ? field.checked : field.value;
  }
  return values;
}

export async function confirmAction(title, text, okText = "Continue") {
  return (await dialog(title, `<p>${esc(text)}</p>`, okText)) !== null;
}

export function method(m) {
  return `<span class="sa-method sa-method--${esc(m)}">${esc(m)}</span>`;
}

export function statusClass(code) {
  if (code < 400) return "sa-status--ok";
  if (code < 500) return "sa-status--client";
  return "sa-status--server";
}

export function json(value) {
  return esc(typeof value === "string" ? value : JSON.stringify(value, null, 2));
}

// The user that the panel acts as when trying endpoints (its session token).
export const session = {
  get() {
    try {
      return JSON.parse(sessionStorage.getItem("silence-admin-session"));
    } catch {
      return null;
    }
  },
  set(value) {
    try {
      if (value) {
        sessionStorage.setItem("silence-admin-session", JSON.stringify(value));
      } else {
        sessionStorage.removeItem("silence-admin-session");
      }
    } catch {
      // Storage blocked: the session is not remembered
    }
    document.dispatchEvent(new CustomEvent("sa-session"));
  },
};

/** Sends a request to the project's API, as the current session (if any). */
export async function callApi(prefix, methodName, path, body) {
  const options = { method: methodName, headers: {} };
  const current = session.get();
  if (current) {
    options.headers.Token = current.token;
  }
  if (body !== undefined && body !== null && methodName !== "GET" && methodName !== "DELETE") {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const started = performance.now();
  const response = await fetch(prefix + path, options);
  const text = await response.text();
  let data = text;
  try {
    data = JSON.parse(text);
  } catch {
    // Not JSON
  }
  return { status: response.status, data, ms: Math.round(performance.now() - started) };
}
