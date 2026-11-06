'use strict';

// Mensajes para el usuario, con las notificaciones de ez-ui.
import { ezToast } from "../ez-ui/js/toast.js";

const messageRenderer = {
  showSuccessMessage: function (message) {
    ezToast(message, "success");
  },

  /** Muestra un error; si viene de la API, añade su motivo (el campo message de la respuesta). */
  showErrorMessage: function (message, error) {
    const reason = error?.response?.data?.message;
    ezToast(reason ? `${message}: ${reason}` : message, "error", 8000);
  },
};

export { messageRenderer };
