/**
 * Muestra un mensaje y devuelve una función para cerrarlo.
 * type: "info", "success", "warning" o "error". duration: milisegundos hasta que se cierra solo
 * (0, nunca). Los parámetros que no se pasan toman su valor por defecto.
 */
export function ezToast(message, type = "info", duration = 4000) {
  const allowedTypes = ["info", "success", "warning", "error"];
  if (!allowedTypes.includes(type)) {
    throw new TypeError("Tipo de toast desconocido");
  }

  // Todas las notificaciones comparten el mismo contenedor.
  let notificationContainer = document.querySelector("#ez-toast-region");
  if (!notificationContainer) {
    notificationContainer = document.createElement("div");
    notificationContainer.id = "ez-toast-region";
    notificationContainer.className = "ez-toast-region";
    notificationContainer.setAttribute("aria-label", "Notificaciones");
    document.body.append(notificationContainer);
  }

  const notification = document.createElement("div");
  notification.className = "ez-toast ez-toast--" + type;

  // Los lectores de pantalla anuncian los errores con mayor urgencia.
  if (type === "error") {
    notification.setAttribute("role", "alert");
  } else {
    notification.setAttribute("role", "status");
  }

  const messageText = document.createElement("span");
  // textContent muestra el mensaje como texto, sin interpretarlo como HTML.
  messageText.textContent = String(message);

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "ez-toast__close";
  closeButton.textContent = "×";
  closeButton.setAttribute("aria-label", "Cerrar notificación");

  notification.append(messageText, closeButton);
  notificationContainer.append(notification);

  let timeoutId;

  function closeNotification() {
    // Si se cierra con el botón, el temporizador deja de ser necesario.
    clearTimeout(timeoutId);
    notification.remove();
  }

  closeButton.addEventListener("click", closeNotification);

  // Una duración de cero mantiene el mensaje hasta que se cierre a mano.
  if (duration > 0) {
    timeoutId = setTimeout(closeNotification, duration);
  }

  return closeNotification;
}
