// JobHunter — comportamiento mínimo del lado del cliente (el resto lo resuelve HTMX).

// Tema claro/oscuro: se guarda en una cookie para que el servidor lo pinte desde el primer render.
document.addEventListener("click", (e) => {
  const themeBtn = e.target.closest("[data-theme-toggle]");
  if (themeBtn) {
    const root = document.documentElement;
    const current = root.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    document.cookie = `theme=${next}; path=/; max-age=31536000; samesite=lax`;
    return;
  }

  // "Por qué este puntaje": abre/cierra el desglose de factores.
  const toggle = e.target.closest("[data-toggle]");
  if (toggle) {
    const panel = document.getElementById(toggle.dataset.toggle);
    if (!panel) return;
    panel.hidden = !panel.hidden;
    toggle.setAttribute("aria-expanded", String(!panel.hidden));
  }
});

// Afinidad mínima: actualiza el texto y el relleno del control mientras se arrastra.
document.addEventListener("input", (e) => {
  if (e.target.id !== "f-min") return;
  const v = e.target.value;
  e.target.style.setProperty("--v", v);
  const out = document.querySelector("[data-min-out]");
  const tpl = document.getElementById("min-hint");
  if (out && tpl) out.textContent = tpl.innerHTML.replace("{n}", v);
});
