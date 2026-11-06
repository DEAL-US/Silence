/** Abre un diálogo y devuelve una Promise con la elección del usuario. */
export function ezConfirm(dialog) {
  if (!(dialog instanceof HTMLDialogElement)) {
    throw new TypeError("ezConfirm espera un elemento <dialog>");
  }

  if (dialog.open) {
    return Promise.reject(new Error("El diálogo ya está abierto"));
  }

  // La elección llega más tarde, cuando el usuario cierra el diálogo.
  // Quien llama puede esperar el resultado con: await ezConfirm(dialog).
  return new Promise(function (resolve) {
    function handleClose() {
      // El botón con value="confirm" indica que el usuario ha confirmado.
      const confirmed = dialog.returnValue === "confirm";
      resolve(confirmed);
    }

    // once elimina este listener después del cierre para no acumularlo al reabrir.
    dialog.addEventListener("close", handleClose, { once: true });

    // Evita reutilizar la respuesta anterior si se cierra con Escape.
    dialog.returnValue = "";
    dialog.showModal();
  });
}
