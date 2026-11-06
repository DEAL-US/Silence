// Statistics of the requests since Silence started (kept in memory).
import { api, esc, attempt, statusClass } from "../ui.js";

const GROUPS = {
  api: ["Your API", "The endpoints of endpoints/*.json"],
  web: ["Your web app", "The files of web/"],
  silence: ["Silence's API", "Login, register and the API summary"],
};

let timer = null;

export async function render(main) {
  main.innerHTML = `
    <h1>Statistics</h1>
    <div class="sa-toolbar">
      <span class="sa-muted" id="since"></span>
      <span class="sa-toolbar__spacer"></span>
      <button class="ez-button ez-button--secondary" type="button" id="reset">Reset</button>
    </div>
    <div class="sa-grid" id="totals"></div>
    <div id="groups"></div>`;
  main.querySelector("#reset").addEventListener("click", async () => {
    await attempt(() => api("/stats", "DELETE"));
    draw(main);
  });
  await draw(main);
  timer = setInterval(() => draw(main), 3000);
}

export function leave() {
  clearInterval(timer);
}

async function draw(main) {
  let s;
  try {
    s = await api("/stats");
  } catch {
    return;
  }
  main.querySelector("#since").textContent = "Since " + new Date(s.since * 1000).toLocaleString() + " (not counting this panel nor the tests)";
  main.querySelector("#totals").innerHTML = Object.entries(GROUPS).map(([g, [title, text]]) => `
    <div class="ez-card"><div class="ez-card__body">
      <p class="sa-muted">${title}</p><p class="sa-big">${s.groups[g].total}</p><p class="sa-small sa-muted">${text}</p>
    </div></div>`).join("");
  main.querySelector("#groups").innerHTML = Object.entries(GROUPS).map(([g, [title]]) => {
    const entries = s.groups[g].entries;
    if (!entries.length) return "";
    return `<section class="sa-section"><h2>${title}</h2><div class="ez-scroll"><table class="sa-table">
      <thead><tr><th>Request</th><th>Count</th><th>Errors</th><th>Status codes</th><th>Average</th></tr></thead>
      <tbody>${entries.map((e) => `<tr>
        <td class="sa-route">${esc(e.key)}</td><td>${e.count}</td><td>${e.errors}</td>
        <td>${Object.entries(e.status).map(([code, n]) => `<span class="sa-status ${statusClass(Number(code))}">${code}</span>×${n}`).join(" ")}</td>
        <td>${e.avgMs} ms</td></tr>`).join("")}</tbody></table></div></section>`;
  }).join("");
}
