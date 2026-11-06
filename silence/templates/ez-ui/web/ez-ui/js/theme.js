/**
 * Botón para cambiar entre el tema claro y el oscuro. Al pulsarlo, cambia
 * data-ez-theme en <html> (tokens.css da otros valores a las variables) y guarda la
 * elección en localStorage, que el navegador conserva al cambiar de página y al
 * cerrarlo; theme-init.js la aplica al cargar cada página. Qué parte del botón se ve
 * (__to-dark o __to-light) lo elige el CSS según el tema (interactive.css).
 */
export function ezThemeToggle(button) {
  button.addEventListener("click", function () {
    const html = document.documentElement;

    let newTheme = "dark";
    if (html.dataset.ezTheme === "dark") {
      newTheme = "light";
    }
    html.dataset.ezTheme = newTheme;

    try {
      localStorage.setItem("ez-ui-theme", newTheme);
    } catch {
      // El navegador puede bloquear el almacenamiento: el tema cambia, sin guardarse.
    }
  });
}
