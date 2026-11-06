/**
 * Aplica el tema que guardó ezThemeToggle (theme.js) antes de que se pinte la página.
 * Es un script clásico, no un módulo: se enlaza en el <head> sin type="module" y se
 * ejecuta en cuanto el navegador lo lee. Un módulo se ejecuta al terminar de leer la
 * página, y se vería un instante el tema claro.
 */
try {
  const savedTheme = localStorage.getItem("ez-ui-theme");
  if (savedTheme === "dark" || savedTheme === "light") {
    document.documentElement.dataset.ezTheme = savedTheme;
  }
} catch {
  // Sin acceso al almacenamiento, se queda el tema claro.
}
