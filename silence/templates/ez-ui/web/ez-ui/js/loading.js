/**
 * Marca un elemento como «cargando» mientras se espera una promesa (una petición a la
 * API) y devuelve su resultado: let players = await ezLoading(gallery, getPlayers());
 * aria-busy="true" muestra el indicador (interactive.css) y avisa a los lectores de
 * pantalla de que el contenido se está actualizando.
 */
export async function ezLoading(element, promise) {
  element.setAttribute("aria-busy", "true");
  try {
    return await promise;
  } finally {
    // finally se ejecuta siempre, también si la petición falla: el indicador se quita.
    element.removeAttribute("aria-busy");
  }
}
