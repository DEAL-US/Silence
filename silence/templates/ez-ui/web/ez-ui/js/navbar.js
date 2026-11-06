/**
 * Menú plegable de una barra de navegación, para las pantallas estrechas: el botón
 * .ez-navbar__toggle muestra u oculta los enlaces. El CSS los oculta mientras el
 * botón tiene aria-expanded="false"; aquí solo se cambia ese atributo.
 */
export function ezNavbar(navbar) {
  // Si el querySelector que la busca no la encuentra, llega null.
  if (!(navbar instanceof Element)) {
    throw new TypeError("ezNavbar espera la barra de navegación (.ez-navbar)");
  }

  const toggle = navbar.querySelector(".ez-navbar__toggle");
  if (!toggle) {
    throw new Error("ezNavbar: la barra no tiene el botón del menú (.ez-navbar__toggle)");
  }

  toggle.addEventListener("click", function () {
    // aria-expanded dice si el menú está desplegado (y lo anuncia el lector de pantalla).
    const isExpanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!isExpanded));
  });
}
