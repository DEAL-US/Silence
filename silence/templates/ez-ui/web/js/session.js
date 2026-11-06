'use strict';

// Sesión del usuario: el token que devuelve el login va en la cabecera Token de cada
// petición (lo añade web/js/api/_auto/common.js, que genera Silence).

const BASE_URL = "/api";

const sessionManager = {
  /** Inicia sesión con el identificador y la contraseña (las columnas que se eligieron en el panel). */
  login: async function (identifierColumn, identifier, password) {
    const body = { [identifierColumn]: identifier, password: password };
    const response = await axios.post(`${BASE_URL}/login`, body);
    sessionStorage.setItem("token", response.data.sessionToken);
    sessionStorage.setItem("user", JSON.stringify(response.data.user));
    return response.data.user;
  },

  logout: function () {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("user");
  },

  isLogged: function () {
    return sessionStorage.getItem("token") !== null;
  },

  getUser: function () {
    return JSON.parse(sessionStorage.getItem("user"));
  },
};

export { sessionManager };
