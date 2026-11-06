'use strict';

import { sessionManager } from "./session.js";
import { messageRenderer } from "./messages.js";

// La columna con la que se identifican los usuarios (la elegida en el panel de Silence)
const IDENTIFIER_COLUMN = "email";

function main() {
  const form = document.querySelector("#login-form");
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const identifier = document.querySelector("#identifier").value;
    const password = document.querySelector("#password").value;
    try {
      await sessionManager.login(IDENTIFIER_COLUMN, identifier, password);
      window.location.href = "index.html";
    } catch (error) {
      messageRenderer.showErrorMessage("No se ha podido iniciar sesión", error);
    }
  });
}

document.addEventListener("DOMContentLoaded", main);
