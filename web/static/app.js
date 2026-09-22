// JobHunter — comportamiento mínimo del lado del cliente (el resto lo resuelve HTMX o el servidor).

// ─── Clics ───────────────────────────────────────────────────────────────────
document.addEventListener("click", (e) => {
  // Tema claro/oscuro: se guarda en una cookie para que el servidor lo pinte desde el primer render.
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

  // Abrir/cerrar un panel ("Por qué este puntaje", portales de un grupo).
  const toggle = e.target.closest("[data-toggle]");
  if (toggle) {
    const panel = document.getElementById(toggle.dataset.toggle);
    if (!panel) return;
    panel.hidden = !panel.hidden;
    toggle.setAttribute("aria-expanded", String(!panel.hidden));
    return;
  }

  // Mostrar/ocultar la clave.
  const reveal = e.target.closest("[data-reveal]");
  if (reveal) {
    const input = document.getElementById(reveal.dataset.reveal);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    reveal.textContent = show ? reveal.dataset.hide : reveal.dataset.show;
    return;
  }

  // "Revisar →": lleva al dato que conviene completar y lo resalta.
  const goto = e.target.closest("[data-goto]");
  if (goto) {
    const target = document.getElementById(goto.dataset.goto);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("attn");
    setTimeout(() => target.classList.remove("attn"), 2200);
    const field = target.querySelector("input:not([type=checkbox]):not([type=radio]), textarea") ||
      (target.matches("input, textarea") ? target : null);
    if (field) setTimeout(() => field.focus({ preventScroll: true }), 400);
  }
});

// Las etiquetas que funcionan como botón (elegir archivo) responden al teclado.
document.addEventListener("keydown", (e) => {
  const label = e.target.closest("label[for][tabindex]");
  if (label && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    document.getElementById(label.htmlFor)?.click();
  }
  // Chips: Enter o coma agregan el texto como chip nuevo, sin enviar el formulario.
  if (e.target.matches("[data-add-name]") && (e.key === "Enter" || e.key === ",")) {
    e.preventDefault();
    addChip(e.target);
  }
});
document.addEventListener("focusout", (e) => {
  if (e.target.matches?.("[data-add-name]")) addChip(e.target);
});

function addChip(input) {
  const value = input.value.replace(/,/g, " ").trim().replace(/\s+/g, " ");
  if (!value) return;
  const list = input.closest("[data-chip-list]");
  const exists = [...list.querySelectorAll("input[type=checkbox]")].find((c) => c.value.toLowerCase() === value.toLowerCase());
  if (exists) {
    exists.checked = true;
  } else {
    const chip = document.createElement("label");
    chip.className = "chip on";
    const box = Object.assign(document.createElement("input"), { type: "checkbox", name: input.dataset.addName, value, checked: true });
    const text = Object.assign(document.createElement("span"), { textContent: value });
    const x = Object.assign(document.createElement("span"), { className: "x", textContent: "×" });
    x.setAttribute("aria-hidden", "true");
    chip.append(box, text, x);
    list.insertBefore(chip, input);
  }
  input.value = "";
  list.dispatchEvent(new Event("change", { bubbles: true }));
}

// ─── Carga del CV: elegir o arrastrar ───────────────────────────────────────
document.addEventListener("change", (e) => {
  if (e.target.matches("[data-autosubmit]") && e.target.files.length) submitUpload(e.target.form);
});

function submitUpload(form) {
  const label = form.querySelector("[data-busy]");
  if (label) label.textContent = label.dataset.busy;
  form.submit();
}

document.addEventListener("dragover", (e) => {
  const zone = e.target.closest("[data-dropzone]");
  if (!zone) return;
  e.preventDefault();
  zone.classList.add("over");
});
document.addEventListener("dragleave", (e) => e.target.closest("[data-dropzone]")?.classList.remove("over"));
document.addEventListener("drop", (e) => {
  const zone = e.target.closest("[data-dropzone]");
  if (!zone || !e.dataTransfer.files.length) return;
  e.preventDefault();
  const input = zone.querySelector("input[type=file]");
  input.files = e.dataTransfer.files;
  submitUpload(zone);
});

// Al enviar, el botón muestra que está trabajando (el análisis del CV tarda unos segundos).
document.addEventListener("submit", (e) => {
  const btn = e.submitter;
  if (btn?.dataset.busy) {
    setTimeout(() => { btn.disabled = true; btn.textContent = btn.dataset.busy; }, 0);
  }
});

// ─── Controles con valor en vivo ────────────────────────────────────────────
document.addEventListener("input", (e) => {
  const t = e.target;
  // Afinidad mínima de resultados.
  if (t.id === "f-min") {
    const v = t.value;
    t.style.setProperty("--v", v);
    const out = document.querySelector("[data-min-out]");
    const tpl = document.getElementById("min-hint");
    if (out && tpl) out.textContent = tpl.innerHTML.replace("{n}", v);
    return;
  }
  // Deslizadores del asistente.
  if (t.matches("[data-range-min]")) {
    const lo = +t.dataset.rangeMin, hi = +t.dataset.rangeMax;
    t.style.setProperty("--v", Math.round(((t.value - lo) / (hi - lo)) * 100));
    const out = document.querySelector(`[data-out="${t.id}"]`);
    if (out) out.textContent = t.value;
    updateSummary(t.form);
  }
});

// Mostrar u ocultar un bloque según un interruptor (email).
document.addEventListener("change", (e) => {
  const sw = e.target.closest("[data-reveals]");
  if (sw) document.getElementById(sw.dataset.reveals).hidden = !sw.checked;
});

// ─── Paso 4: grupos de portales y resumen ──────────────────────────────────
document.addEventListener("change", (e) => {
  const form = e.target.closest("[data-search-form]");
  if (!form) return;
  const group = e.target.closest("[data-group]");
  if (group) {
    const boxes = [...group.querySelectorAll("input[name=portal]")];
    if (e.target.matches("[data-group-toggle]")) boxes.forEach((b) => { b.checked = e.target.checked; });
    const on = boxes.filter((b) => b.checked).length;
    const toggle = group.querySelector("[data-group-toggle]");
    toggle.checked = on === boxes.length;
    toggle.indeterminate = on > 0 && on < boxes.length;
    group.querySelector("[data-group-count]").textContent = on;
  }
  updateSummary(form);
});

function updateSummary(form) {
  if (!form?.matches("[data-search-form]")) return;
  const count = (sel) => form.querySelectorAll(sel).length;
  const set = (key, value) => { const el = form.querySelector(`[data-sum="${key}"]`); if (el) el.textContent = value; };
  set("terms", count("input[name=terms]:checked"));
  const portals = count("input[name=portal]:checked");
  set("portals", portals);
  const mods = [...form.querySelectorAll("input[name=modality]:checked")].map((b) => b.nextElementSibling.textContent);
  const modEl = form.querySelector('[data-sum="modality"]');
  if (modEl) modEl.textContent = mods.length ? mods.join(", ") : modEl.dataset.any;
  const n = +(form.querySelector("[name=eval_limit]")?.value || 40);
  set("eval", n);
  // Misma estimación que web/wizard.py:estimate_minutes.
  const rpm = +form.dataset.rpm || 15;
  const calls = Math.ceil(n / 5) + Math.min(10, n) + 1;
  set("minutes", Math.max(1, Math.ceil(0.12 * portals + calls / rpm)));
}

document.querySelectorAll("[data-group]").forEach((group) => {
  const boxes = [...group.querySelectorAll("input[name=portal]")];
  const on = boxes.filter((b) => b.checked).length;
  const toggle = group.querySelector("[data-group-toggle]");
  if (toggle) toggle.indeterminate = on > 0 && on < boxes.length;
});
