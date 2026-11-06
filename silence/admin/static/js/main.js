// Admin panel of Silence: a single page with one view per hash (#/endpoints...).
import { ezNavbar } from "../ez-ui/js/navbar.js";
import { ezThemeToggle } from "../ez-ui/js/theme.js";
import { api, esc, session } from "./ui.js";
import * as overview from "./pages/overview.js";
import * as database from "./pages/database.js";
import * as users from "./pages/users.js";
import * as endpoints from "./pages/endpoints.js";
import * as tests from "./pages/tests.js";
import * as stats from "./pages/stats.js";

const routes = {
  "": overview,
  database,
  users,
  endpoints,
  tests,
  stats,
};

let current = null;

export const app = {
  status: null,
  async refreshStatus() {
    try {
      this.status = await api("/status");
    } catch {
      return this.status;
    }
    const s = this.status;
    document.querySelector("#project-name").textContent = s.project;
    document.querySelector("#version").textContent = "Silence v" + s.version;
    document.querySelector("#link-api").href = s.apiPrefix;
    const dot = document.querySelector("#dot-database");
    dot.className = "sa-dot " + (s.database.error ? "sa-dot--error" : "sa-dot--ok");
    dot.title = s.database.error || s.database.name;
    document.querySelector("#count-endpoints").textContent = s.endpoints.count || "";
    document.querySelector("#count-tests").textContent = s.tests.count || "";
    return s;
  },
};

function showSession() {
  const box = document.querySelector("#acting-as");
  const current = session.get();
  box.hidden = !current;
  if (current) {
    box.innerHTML = `Trying the API as <strong>${esc(current.label)}</strong>
      <button class="ez-button ez-button--secondary sa-button--small" type="button" id="end-session">End</button>`;
    box.querySelector("#end-session").addEventListener("click", () => session.set(null));
  }
}

async function render() {
  const name = location.hash.replace(/^#\/?/, "").split("/")[0];
  const page = routes[name] ?? overview;
  for (const link of document.querySelectorAll(".ez-navbar__links a")) {
    const target = link.getAttribute("href").replace(/^#\/?/, "");
    if (target === name) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
  if (current?.leave) {
    current.leave();
  }
  current = page;
  const main = document.querySelector("#page");
  main.innerHTML = "";
  await app.refreshStatus();
  await page.render(main, app);
}

function main() {
  ezNavbar(document.querySelector(".ez-navbar"));
  ezThemeToggle(document.querySelector("#theme"));
  document.addEventListener("sa-session", showSession);
  window.addEventListener("hashchange", render);
  showSession();
  render();
}

document.addEventListener("DOMContentLoaded", main);
