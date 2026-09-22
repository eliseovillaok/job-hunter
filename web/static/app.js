// JobHunter — comportamiento del lado del cliente. La navegación la hace HTMX (hx-boost, sin recargas);
// acá van las microinteracciones. Todo se engancha por delegación, así sobrevive a los reemplazos de HTMX.

const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const hasVT = typeof document.startViewTransition === "function";
document.documentElement.classList.toggle("no-vt", !hasVT);


// ─── Abrir/cerrar con animación de altura ────────────────────────────────────
// El estado final nunca depende de que la animación termine: si el navegador no la ejecuta
// (pestaña en segundo plano, ahorro de energía), un temporizador deja igual el resultado.
function animateThen(anim, ms, done) {
  let ran = false;
  const finish = () => { if (!ran) { ran = true; done(); } };
  if (anim) anim.addEventListener("finish", finish);
  setTimeout(finish, ms);
}

function slide(el, show) {
  if (show === !el.hidden) return;
  if (reduceMotion() || !el.animate) { el.hidden = !show; return; }
  el.hidden = false;
  const h = el.scrollHeight;
  const frames = [{ height: "0px", opacity: 0, overflow: "hidden" }, { height: `${h}px`, opacity: 1, overflow: "hidden" }];
  const anim = el.animate(show ? frames : frames.reverse(), { duration: 220, easing: "cubic-bezier(.2,.7,.2,1)" });
  animateThen(anim, 260, () => { if (!show) el.hidden = true; });
}

// ─── Clics ───────────────────────────────────────────────────────────────────
document.addEventListener("click", (e) => {
  // Tocar un ⓘ abre su tooltip (en móvil no hay hover). Si está dentro de un <label>, no debe activar el campo.
  const tip = e.target.closest(".tt");
  if (tip) {
    e.preventDefault();
    tip.focus();
    placeTip(tip);
    return;
  }

  // Tema claro/oscuro con fundido (se guarda en una cookie para que el servidor lo pinte desde el primer render).
  const themeBtn = e.target.closest("[data-theme-toggle]");
  if (themeBtn) {
    const root = document.documentElement;
    const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    const apply = () => { root.dataset.theme = next; };
    document.cookie = `theme=${next}; path=/; max-age=31536000; samesite=lax`;
    if (hasVT && !reduceMotion()) {
      root.classList.add("theme-vt");
      const vt = document.startViewTransition(apply);
      vt.ready.catch(() => {});   // el navegador puede saltearla (pestaña oculta): el tema igual se aplica
      vt.finished.catch(() => {}).finally(() => root.classList.remove("theme-vt"));
    } else apply();
    return;
  }

  // Enlaces del menú a secciones de la landing: desplazamiento suave si ya estamos en ella.
  const anchor = e.target.closest("a[data-smooth]");
  if (anchor) {
    const url = new URL(anchor.href);
    if (url.pathname === location.pathname && url.hash) {
      const target = document.querySelector(url.hash);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth" });
        history.replaceState(null, "", url.hash);
      }
    }
    return;
  }

  // Volver arriba.
  if (e.target.closest("[data-to-top]")) {
    window.scrollTo({ top: 0, behavior: reduceMotion() ? "auto" : "smooth" });
    return;
  }

  // Volver a un paso anterior: la tarjeta entra desde la izquierda.
  if (e.target.closest("[data-back]")) document.documentElement.dataset.nav = "back";

  // Paso 1: alternar entre subir el CV y escribir el perfil.
  const modeBtn = e.target.closest("[data-mode-switch]");
  if (modeBtn) {
    const card = modeBtn.closest("[data-step1]");
    const mode = modeBtn.dataset.modeSwitch;
    card.querySelectorAll("[data-mode]").forEach((el) => slide(el, el.dataset.mode === mode));
    card.querySelectorAll("[data-mode-title]").forEach((el) => { el.hidden = el.dataset.modeTitle !== mode; });
    const railSub = document.querySelector("[data-rail-sub1]");
    if (railSub) railSub.textContent = railSub.dataset[mode === "write" ? "write" : "upload"];
    if (mode === "write") {
      // El servidor pasa a "perfil escrito a mano" para poder guardar el borrador.
      fetch("/asistente/manual", { method: "POST", body: new URLSearchParams(), redirect: "manual" });
      setTimeout(() => card.querySelector("textarea")?.focus(), 230);
    }
    return;
  }

  // Quitar una etiqueta.
  const removeChip = e.target.closest("[data-chip-list] .x");
  if (removeChip) {
    const chip = removeChip.closest(".chip");
    const list = chip.parentElement;
    const drop = () => {
      chip.remove();
      list.dispatchEvent(new Event("change", { bubbles: true }));
      refreshRow(list.closest("[data-row]"));
    };
    const fade = chip.animate && !reduceMotion()
      ? chip.animate([{ opacity: 1, transform: "scale(1)" }, { opacity: 0, transform: "scale(.85)" }], { duration: 140, easing: "ease" })
      : null;
    animateThen(fade, 170, drop);
    return;
  }

  // "+ Agregar" de una lista de etiquetas.
  const addBtn = e.target.closest("[data-add-to]");
  if (addBtn) { openChipInput(addBtn); return; }

  // Filas "dato · valor · Editar": se abre solo la que se quiere cambiar.
  const editBtn = e.target.closest("[data-edit]");
  if (editBtn) {
    const row = editBtn.closest("[data-row]");
    const panel = row.querySelector(".re");
    const open = panel.hidden;
    slide(panel, open);
    row.classList.toggle("open", open);
    editBtn.textContent = open ? editBtn.dataset.done : editBtn.dataset.label;
    if (open) setTimeout(() => panel.querySelector("input:not([type=hidden]), textarea, .chip-add")?.focus({ preventScroll: true }), 220);
    else refreshRow(row);
    return;
  }

  // Abrir/cerrar un panel ("Por qué este puntaje", portales de un grupo).
  const toggle = e.target.closest("[data-toggle]");
  if (toggle) {
    const panel = document.getElementById(toggle.dataset.toggle);
    if (!panel) return;
    const show = panel.hidden;
    slide(panel, show);
    toggle.setAttribute("aria-expanded", String(show));
    rememberOpen(toggle.dataset.toggle, show);
    return;
  }

  // <details> con animación (opciones avanzadas).
  const summary = e.target.closest("details.how > summary");
  if (summary && !reduceMotion()) {
    e.preventDefault();
    const details = summary.parentElement;
    const body = [...details.children].filter((c) => c !== summary);
    if (!details.open) {
      details.open = true;
      rememberOpen(details.id || summary.textContent.trim(), true);
      body.forEach((b) => { b.hidden = true; slide(b, true); });
    } else {
      rememberOpen(details.id || summary.textContent.trim(), false);
      body.forEach((b) => slide(b, false));
      setTimeout(() => { details.open = false; body.forEach((b) => { b.hidden = false; }); }, 260);
    }
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
    target.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "center" });
    target.classList.add("attn");
    setTimeout(() => target.classList.remove("attn"), 2200);
    const rowEdit = target.matches("[data-row]") ? target.querySelector("[data-edit]") : null;
    if (rowEdit && target.querySelector(".re")?.hidden) rowEdit.click();
    const field = target.querySelector("input:not([type=checkbox]):not([type=radio]), textarea") ||
      (target.matches("input, textarea") ? target : null);
    if (field) setTimeout(() => field.focus({ preventScroll: true }), 400);
  }
});

// ─── Teclado ─────────────────────────────────────────────────────────────────
document.addEventListener("keydown", (e) => {
  const label = e.target.closest("label[for][tabindex]");
  if (label && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    document.getElementById(label.htmlFor)?.click();
  }
  // Escape cierra el tooltip abierto.
  if (e.key === "Escape" && document.activeElement?.closest(".tt")) document.activeElement.blur();
});
function addChip(input) {
  const list = input.closest("[data-chip-list]");
  const value = input.value.replace(/,/g, " ").trim().replace(/\s+/g, " ");
  const name = list.dataset.chipList;
  input.value = "";
  if (!value) return;
  const exists = [...list.querySelectorAll(`input[name="${name}"]`)]
    .find((h) => h.value.toLowerCase() === value.toLowerCase());
  if (exists) {                                    // ya está: se resalta en vez de duplicar
    const chip = exists.closest(".chip");
    chip.classList.remove("added"); void chip.offsetWidth; chip.classList.add("added");
    return;
  }
  const chip = document.createElement("span");
  chip.className = "chip added";
  const hidden = Object.assign(document.createElement("input"), { type: "hidden", name, value });
  const text = Object.assign(document.createElement("span"), { className: "txt", textContent: value });
  const x = Object.assign(document.createElement("button"), { type: "button", className: "x", textContent: "×" });
  x.setAttribute("aria-label", `Quitar ${value}`);
  chip.append(hidden, text, x);
  list.insertBefore(chip, input.closest(".chip-add-wrap") || input);
  list.dispatchEvent(new Event("change", { bubbles: true }));
  refreshRow(list.closest("[data-row]"));
}

// "+ Agregar" abre un campo en el lugar; Enter agrega, Escape cancela.
function openChipInput(btn) {
  const list = btn.closest("[data-chip-list]");
  const wrap = document.createElement("span");
  wrap.className = "chip-add-wrap";
  const input = Object.assign(document.createElement("input"), {
    type: "text", className: "chip-add-field", placeholder: btn.dataset.placeholder, maxLength: 80,
  });
  input.setAttribute("aria-label", btn.dataset.placeholder);
  wrap.append(input);
  list.insertBefore(wrap, btn);
  btn.hidden = true;
  input.focus();
  const close = () => { wrap.remove(); btn.hidden = false; };
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === ",") { ev.preventDefault(); addChip(input); }
    if (ev.key === "Escape") { ev.preventDefault(); close(); btn.focus(); }
  });
  input.addEventListener("blur", () => { addChip(input); setTimeout(close, 0); });
}

// ─── Tooltips: que nunca se corten contra el borde de la pantalla ────────────
function placeTip(host) {
  const tip = host.querySelector(".tt-b");
  if (!tip) return;
  tip.style.setProperty("--tt-shift", "0px");
  const r = tip.getBoundingClientRect();
  const margin = 12;
  let shift = 0;
  if (r.right > innerWidth - margin) shift = innerWidth - margin - r.right;
  if (r.left + shift < margin) shift = margin - r.left;
  tip.style.setProperty("--tt-shift", `${Math.round(shift)}px`);
}
["mouseover", "focusin"].forEach((ev) => document.addEventListener(ev, (e) => {
  const host = e.target.closest?.(".tt, .chip.skill");
  if (host) placeTip(host);
}));

// ─── Carga del CV: elegir o arrastrar ───────────────────────────────────────
document.addEventListener("change", (e) => {
  if (e.target.matches("[data-autosubmit]") && e.target.files.length) submitUpload(e.target.form, e.target.files[0]);
});

function submitUpload(form, file) {
  const name = form.querySelector("[data-file-name]");
  if (name && file) name.textContent = file.name;
  // El aviso "Subiendo…" solo si tarda: si el paso siguiente llega enseguida, no se ve un destello.
  delayedBusy(() => {
    form.classList.add("busy");
    const label = form.querySelector("label.btn");
    if (label && form.classList.contains("drop") && label.dataset.busy) label.textContent = label.dataset.busy;
  });
  form.requestSubmit();   // pasa por HTMX (sin recarga) con la transición al paso siguiente
}

// Los estados de espera aparecen recién si la acción tarda; si no, se pasa directo.
let busyTimer = null;
function delayedBusy(fn) {
  clearTimeout(busyTimer);
  busyTimer = setTimeout(fn, 220);
}
document.addEventListener("htmx:beforeSwap", () => clearTimeout(busyTimer));

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
  zone.classList.remove("over");
  const input = zone.querySelector("input[type=file]");
  input.files = e.dataTransfer.files;
  submitUpload(zone, e.dataTransfer.files[0]);
});

// ─── Envíos: sin doble clic y con el botón mostrando que trabaja ─────────────
document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.dataset.sending) { e.preventDefault(); return; }
  form.dataset.sending = "1";
  const btn = e.submitter;
  if (btn) {
    setTimeout(() => { btn.disabled = true; }, 0);   // evita el doble envío desde el primer instante
    if (btn.dataset.busy) delayedBusy(() => { btn.innerHTML = `<span class="spin"></span> ${btn.dataset.busy}`; });
  }
}, true);
// Si el servidor devuelve la misma página (error de validación), el formulario vuelve a estar disponible.
document.addEventListener("htmx:afterRequest", (e) => {
  const form = e.detail.elt.closest?.("form") || e.detail.elt;
  if (form?.dataset) delete form.dataset.sending;
});

// ─── Guardado automático: antes de navegar, se envía lo pendiente ───────────
document.addEventListener("input", (e) => e.target.closest(".autosave, [hx-post*='borrador']")?.setAttribute("data-dirty", ""));
document.addEventListener("change", (e) => e.target.closest(".autosave, [hx-post*='borrador']")?.setAttribute("data-dirty", ""));
document.addEventListener("htmx:afterRequest", (e) => {
  if ((e.detail.pathInfo?.requestPath || "").includes("/borrador/")) e.detail.elt.removeAttribute("data-dirty");
});
document.addEventListener("htmx:confirm", (e) => {
  const dirty = document.querySelector("[data-dirty]");
  const elt = e.detail.elt;
  if (!dirty || dirty === elt || dirty.contains(elt) || dirty.closest("form")?.contains(elt)) return;
  e.preventDefault();
  const form = dirty.closest("form");
  const url = dirty.getAttribute("hx-post");
  fetch(url, { method: "POST", body: new FormData(form) })
    .finally(() => { dirty.removeAttribute("data-dirty"); e.detail.issueRequest(true); });
});

// ─── Resumen de cada fila, siempre al día ───────────────────────────────────
function refreshRow(row) {
  if (!row) return;
  const preview = row.querySelector("[data-preview], [data-where-preview], [data-portals-preview], [data-adv-preview]");
  if (!preview) return;
  const txt = (el) => el.textContent.trim();
  const fallback = preview.dataset.any || "—";

  if (preview.hasAttribute("data-portals-preview")) {
    const n = row.querySelectorAll("input[name=portal]:checked").length;
    preview.textContent = (preview.dataset.tpl || "{n}").replace("{n}", n);
    return;
  }
  if (preview.hasAttribute("data-adv-preview")) {
    const score = row.querySelector("[name=min_score]")?.value ?? "";
    const n = row.querySelector("[name=eval_limit]")?.value ?? "";
    preview.textContent = (preview.dataset.tpl || "").replace("{score}", score).replace("{n}", n);
    return;
  }
  if (preview.hasAttribute("data-where-preview")) {
    const mods = [...row.querySelectorAll("input[name=modality]:checked")].map((b) => txt(b.nextElementSibling));
    const langs = [...row.querySelectorAll("input[name=job_lang]:checked")].map((b) => txt(b.nextElementSibling));
    const place = row.querySelector("[name=locations]")?.value.trim();
    preview.textContent = [mods.length ? mods.join(", ") : fallback, place, langs.join(", ")].filter(Boolean).join(" · ");
    return;
  }
  const chips = row.querySelector("[data-chip-list]");
  if (chips) {
    const names = [...chips.querySelectorAll(".chip .txt")].map((c) => txt(c).replace(/\s+·.*$/, ""));
    preview.textContent = names.join(", ") || fallback;
    return;
  }
  const radio = row.querySelector("input[type=radio]:checked");
  if (radio) { preview.textContent = txt(radio.nextElementSibling); return; }
  const field = row.querySelector("input:not([type=hidden]), textarea");
  if (field) preview.textContent = field.value.trim() || fallback;
}

document.addEventListener("input", (e) => refreshRow(e.target.closest("[data-row]")));
document.addEventListener("change", (e) => refreshRow(e.target.closest("[data-row]")));

// ─── Errores: se borran en cuanto el usuario corrige el campo ───────────────
document.addEventListener("input", (e) => {
  const field = e.target.closest("[name]");
  if (!field || !field.classList.contains("has-error")) return;
  field.classList.remove("has-error");
  field.removeAttribute("aria-invalid");
  const msg = document.querySelector(`[data-err-for="${field.name}"]`);
  if (msg) msg.hidden = true;
});

// ─── Controles con valor en vivo ────────────────────────────────────────────
document.addEventListener("input", (e) => {
  const t = e.target;
  if (t.id === "f-min") {   // afinidad mínima en resultados
    t.style.setProperty("--v", t.value);
    const out = document.querySelector("[data-min-out]");
    const tpl = document.getElementById("min-hint");
    if (out && tpl) out.textContent = tpl.innerHTML.replace("{n}", t.value);
    return;
  }
  if (t.matches("[data-range-min]")) {   // deslizadores del asistente
    const lo = +t.dataset.rangeMin, hi = +t.dataset.rangeMax;
    t.style.setProperty("--v", Math.round(((t.value - lo) / (hi - lo)) * 100));
    const out = document.querySelector(`[data-out="${t.id}"]`);
    if (out) out.textContent = t.value;
    updateSummary(t.form);
  }
  if (t.matches("[data-enables]")) syncEnables(t);
});

// Un campo que habilita el botón principal (perfil escrito a mano).
function syncEnables(field) {
  const btn = document.getElementById(field.dataset.enables);
  if (!btn) return;
  const ok = field.value.trim().length > 0;
  if (ok && btn.disabled) { btn.classList.remove("ready"); void btn.offsetWidth; btn.classList.add("ready"); }
  btn.disabled = !ok;
  const hint = document.querySelector(`[data-enabled-hint="${btn.id}"]`);
  if (hint) hint.hidden = ok;
}

// Mostrar u ocultar un bloque según un interruptor (email).
document.addEventListener("change", (e) => {
  const sw = e.target.closest("[data-reveals]");
  if (sw) slide(document.getElementById(sw.dataset.reveals), sw.checked);
});

// ─── Paso 4: grupos de portales y resumen ──────────────────────────────────
document.addEventListener("change", (e) => {
  const form = e.target.closest("[data-search-form]");
  if (!form) return;
  const group = e.target.closest("[data-group]");
  if (group) {
    const boxes = [...group.querySelectorAll("input[name=portal]")];
    if (e.target.matches("[data-group-toggle]")) boxes.forEach((b) => { b.checked = e.target.checked; });
    syncGroup(group);
    refreshRow(group.closest("[data-row]"));   // el resumen de la fila, después de aplicar el cambio
  }
  updateSummary(form);
});

function syncGroup(group) {
  const boxes = [...group.querySelectorAll("input[name=portal]")];
  const on = boxes.filter((b) => b.checked).length;
  const toggle = group.querySelector("[data-group-toggle]");
  if (toggle) { toggle.checked = on === boxes.length; toggle.indeterminate = on > 0 && on < boxes.length; }
  const count = group.querySelector("[data-group-count]");
  if (count) count.textContent = on;
}

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

// ─── Volver arriba ──────────────────────────────────────────────────────────
let ticking = false;
addEventListener("scroll", () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    document.querySelector("[data-to-top]")?.classList.toggle("show", scrollY > 480);
    ticking = false;
  });
}, { passive: true });

// ─── Al cargar y después de cada navegación de HTMX ─────────────────────────
// Lo que el usuario abrió sigue abierto al cambiar de idioma o volver a la pantalla (por pestaña).
const OPEN_KEY = "jh-open";
function openState() {
  try { return JSON.parse(sessionStorage.getItem(OPEN_KEY)) || {}; } catch { return {}; }
}
function rememberOpen(id, open) {
  if (!id) return;
  try {
    const state = openState();
    if (open) state[id] = 1; else delete state[id];
    sessionStorage.setItem(OPEN_KEY, JSON.stringify(state));
  } catch { /* modo privado: no es crítico */ }
}
function restoreOpen(root) {
  const state = openState();
  Object.keys(state).forEach((id) => {
    const panel = root.querySelector?.(`#${CSS.escape(id)}`) || document.getElementById(id);
    if (!panel) return;
    if (panel.tagName === "DETAILS") { panel.open = true; return; }
    panel.hidden = false;
    const toggle = document.querySelector(`[data-toggle="${CSS.escape(id)}"]`);
    if (toggle) toggle.setAttribute("aria-expanded", "true");
  });
}

function init(root = document) {
  // ?lang= y ?theme= ya quedaron guardados en cookies: se quitan de la URL para que recargar no los pise.
  const url = new URL(location.href);
  if (url.searchParams.has("lang") || url.searchParams.has("theme")) {
    url.searchParams.delete("lang");
    url.searchParams.delete("theme");
    history.replaceState(history.state, "", url.pathname + url.search + url.hash);
  }
  const page = document.querySelector("[data-page]");
  if (page?.dataset.lang) document.documentElement.lang = page.dataset.lang;
  const top = document.querySelector("[data-to-top]");
  if (top) { top.hidden = false; top.classList.toggle("show", scrollY > 480); }
  const firstError = document.querySelector(".has-error");
  if (firstError) firstError.focus({ preventScroll: false });
  restoreOpen(root);
  root.querySelectorAll("[data-edit]").forEach((b) => { b.dataset.label = b.dataset.label || b.textContent.trim(); });
  root.querySelectorAll("[data-group]").forEach(syncGroup);
  root.querySelectorAll("[data-enables]").forEach(syncEnables);
  // Entrada desde otra página con #sección: desplazamiento suave hasta ella.
  if (location.hash && root === document) {
    const target = document.querySelector(location.hash);
    if (target) setTimeout(() => target.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth" }), 120);
  }
}
init();
document.addEventListener("htmx:afterSettle", (e) => {
  init(e.detail.elt || document);
  delete document.documentElement.dataset.nav;
});
