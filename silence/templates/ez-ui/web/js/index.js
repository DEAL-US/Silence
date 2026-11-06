'use strict';

import { ezNavbar } from "../ez-ui/js/navbar.js";
import { sessionManager } from "./session.js";

function showUser() {
  const logged = sessionManager.isLogged();
  document.querySelector("#nav-login").hidden = logged;
  document.querySelector("#nav-user").hidden = !logged;
  if (logged) {
    const user = sessionManager.getUser();
    document.querySelector("#user-name").textContent = Object.values(user)[1] ?? "";
  }
}

function main() {
  ezNavbar(document.querySelector(".ez-navbar"));
  showUser();
  document.querySelector("#logout").addEventListener("click", function (event) {
    event.preventDefault();
    sessionManager.logout();
    showUser();
  });
}

document.addEventListener("DOMContentLoaded", main);
