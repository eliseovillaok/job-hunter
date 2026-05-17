"""
app.py — Job Hunter UI con Streamlit
"""

import streamlit as st
import json
import time
import os
from datetime import datetime
from pathlib import Path

# ─── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Hunter AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════
   JOB HUNTER AI — Design System
   ═══════════════════════════════════════════════════════════════════ */

/* ── Layout ──────────────────────────────────────────────────────── */
div.block-container,
div[data-testid="stMainBlockContainer"] {
    max-width: 860px !important;
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
section[data-testid="stSidebar"] { display: none; }
button[data-testid="collapsedControl"] { display: none; }

/* ── Buttons — smooth lift & glow ────────────────────────────────── */
button[data-testid^="baseButton"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease,
                background 0.15s ease, border-color 0.15s ease !important;
    will-change: transform !important;
}
button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.28) !important;
}
button[data-testid="baseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(79,70,229,0.38) !important;
}
button[data-testid="baseButton-primary"]:active {
    transform: translateY(0px) !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.28) !important;
}
button[data-testid="baseButton-secondary"] {
    background: #ffffff !important;
    border: 1.5px solid #d1d5db !important;
    color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
button[data-testid="baseButton-secondary"]:hover {
    transform: translateY(-1px) !important;
    border-color: #6366f1 !important;
    color: #4f46e5 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.09) !important;
}

/* ── Inputs & textareas ──────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border: 1.5px solid #d1d5db !important;
    border-radius: 8px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
    outline: none !important;
}

/* ── Selectbox / multiselect ─────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div:first-child {
    border: 1.5px solid #d1d5db !important;
    border-radius: 8px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:first-child:focus-within {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
}

/* ── Containers (border=True) ────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    border: 1.5px solid #e5e7eb !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    transition: box-shadow 0.18s ease !important;
    overflow: hidden !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.08) !important;
}

/* ── Expanders ───────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    border: 1.5px solid #e5e7eb !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    transition: box-shadow 0.18s ease !important;
}
div[data-testid="stExpander"]:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.07) !important;
}

/* ── File uploader ───────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed #c7d2fe !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg, #fafafe 0%, #f0f4ff 100%) !important;
    transition: border-color 0.15s ease, background 0.15s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #6366f1 !important;
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%) !important;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
[data-testid="stTabs"] button[role="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500 !important;
    transition: color 0.15s ease !important;
}

/* ── Metric cards ────────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
}

/* ── Keywords form (no extra border) ────────────────────────────── */
div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* ── Score / source badges ───────────────────────────────────────── */
.score-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 14px;
}
.score-high   { background: #dcfce7; color: #15803d; }
.score-medium { background: #fef9c3; color: #a16207; }
.score-low    { background: #f1f5f9; color: #64748b; }
.source-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    color: white;
}
.src-remotive  { background: #6366f1; }
.src-arbeitnow { background: #0ea5e9; }
.src-wwr       { background: #10b981; }
.src-himalayas { background: #f59e0b; }

/* ── Cover letter ────────────────────────────────────────────────── */
.cover-letter-box {
    background: #f8fafc;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    padding: 20px 24px;
    font-family: Georgia, serif;
    font-size: 14px;
    line-height: 1.85;
    white-space: pre-wrap;
}

/* ── Feature cards (empty state) ────────────────────────────────── */
.feature-card {
    background: #ffffff;
    border: 1.5px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.5rem 1rem 1.25rem 1rem;
    text-align: center;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.09);
    border-color: #c7d2fe;
}
.feature-icon { font-size: 2rem; display: block; margin-bottom: 0.65rem; }
.feature-title { font-weight: 700; font-size: 1rem; color: #111827; margin-bottom: 0.3rem; }
.feature-desc  { color: #6b7280; font-size: 0.82rem; line-height: 1.5; }

/* ── Cancel button (rojo) ────────────────────────────────────────── */
[data-testid="stMarkdownContainer"]:has(.cancel-marker) ~ [data-testid="stButton"] > button {
    background-color: #fff5f5 !important;
    color: #dc2626 !important;
    border: 1.5px solid #fca5a5 !important;
    box-shadow: none !important;
}
[data-testid="stMarkdownContainer"]:has(.cancel-marker) ~ [data-testid="stButton"] > button:hover {
    background-color: #fee2e2 !important;
    border-color: #ef4444 !important;
    transform: none !important;
    box-shadow: 0 2px 8px rgba(220,38,38,0.18) !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
# Nada se guarda en disco: cada sesión de navegador empieza limpia.
# Los datos persisten mientras la pestaña esté abierta.
_defaults = {
    "show_dialog":        False,
    "config_step":        1,
    "cv_analyzed":        False,
    "run_search":         False,
    "search_done":        False,
    "gemini_key":         "",
    "selected_model":     "models/gemini-3.1-flash-lite",
    "send_email":         False,
    "email_sender":       "",
    "email_password_raw": "",
    "email_recipient":    "",
    "keywords_list":      [
        "frontend developer", "react developer", "full stack engineer",
        "UI engineer", "javascript developer",
    ],
    "min_score":          65,
    "use_max_results":    False,
    "max_results_limit":  100,
    "use_remotive":       True,
    "use_arbeitnow":      True,
    "use_wwr":            True,
    "use_himalayas":      True,
    "candidate_profile":  """Rol buscado: Frontend Engineer / Full Stack (solo remoto)

Stack técnico:
- JavaScript, React, Vue.js, HTML5, CSS3
- Node.js, Express, API REST
- PostgreSQL, MongoDB
- Git, GitHub, Webpack
- Testing: Jest, React Testing Library

Experiencia:
- Senior Frontend Engineer en StartupXYZ (2 años)
- Mid-level Developer en TechCorp (1.5 años)
- Freelance projects en React y Vue

Idiomas: Español (nativo), Inglés (fluido)
Ubicación: Cualquier zona horaria — 100% remoto""",
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─── Helpers ──────────────────────────────────────────────────────────────────
def validate_config():
    errors = []
    if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
        errors.append("API key de Gemini inválida.")
    if st.session_state.send_email:
        if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
            errors.append("Email de envío inválido.")
        if len(st.session_state.email_password_raw.replace(" ", "")) != 16:
            errors.append("La contraseña de app debe tener 16 caracteres.")
        if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
            errors.append("Email destinatario inválido.")
    if not st.session_state.keywords_list:
        errors.append("Agregá al menos una keyword.")
    if not any([st.session_state.use_remotive, st.session_state.use_arbeitnow,
                st.session_state.use_wwr, st.session_state.use_himalayas]):
        errors.append("Seleccioná al menos una fuente.")
    return errors


def format_duration(seconds):
    seconds = max(0, int(round(seconds)))
    m, s = divmod(seconds, 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


def _render_stepper(step: int) -> None:
    labels = ["Credenciales", "Tu CV", "Búsqueda", "Perfil"]
    parts = []
    for i, label in enumerate(labels, 1):
        done = i < step
        active = i == step
        if done:
            bg, fg, brd, lc, fw, content = "#4f46e5", "white", "#4f46e5", "#4f46e5", "500", "✓"
        elif active:
            bg, fg, brd, lc, fw, content = "#4f46e5", "white", "#4f46e5", "#1e293b", "700", str(i)
        else:
            bg, fg, brd, lc, fw, content = "#f1f5f9", "#94a3b8", "#e2e8f0", "#94a3b8", "400", str(i)

        dot = (
            f'<div style="width:36px;height:36px;border-radius:50%;background:{bg};color:{fg};'
            f'border:2px solid {brd};display:flex;align-items:center;justify-content:center;'
            f'font-size:15px;font-weight:700;flex-shrink:0;">{content}</div>'
        )
        lbl = f'<div style="font-size:12px;color:{lc};font-weight:{fw};white-space:nowrap;margin-top:4px;">{label}</div>'
        parts.append(
            f'<div style="display:flex;flex-direction:column;align-items:center;">{dot}{lbl}</div>'
        )
        if i < len(labels):
            line = "#4f46e5" if done else "#e2e8f0"
            parts.append(
                f'<div style="height:2px;width:80px;background:{line};'
                f'margin-bottom:22px;flex-shrink:0;"></div>'
            )

    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:center;'
        f'margin:0.5rem 0 0.75rem 0;">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def _analyze_cv(uploaded_file, api_key: str, model: str) -> dict | None:
    """Envía el CV a Gemini y devuelve {keywords, profile}."""
    import json, re
    from google import genai
    from google.genai import types

    _PROMPT = (
        "Analyze this CV/resume carefully. "
        "Return ONLY a raw JSON object — no markdown, no explanation:\n"
        '{"keywords": ["8 to 12 specific job-board search terms matching this person\'s role and stack, '
        'e.g. \\"frontend developer\\", \\"react engineer\\", \\"senior fullstack\\""], '
        '"profile": "Candidate profile in the same language as the CV. '
        "Include: target role, full tech stack, years of experience, key achievements, "
        'spoken languages, and remote/location preference. 3-4 concise paragraphs."}'
    )

    try:
        _client = genai.Client(api_key=api_key)
        file_bytes = uploaded_file.getvalue()
        mime = uploaded_file.type  # "application/pdf" or "text/plain"

        if mime == "text/plain":
            cv_text = file_bytes.decode("utf-8", errors="replace")[:10000]
            contents = f"{_PROMPT}\n\nCV:\n{cv_text}"
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            import io
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(file_bytes))
            cv_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())[:10000]
            contents = f"{_PROMPT}\n\nCV:\n{cv_text}"
        else:
            contents = [
                types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                types.Part.from_text(_PROMPT),
            ]

        resp = _client.models.generate_content(model=model, contents=contents)
        raw = resp.text.strip().replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                return json.loads(m.group())
        return None
    except Exception as e:
        st.error(f"Error analizando el CV: {e}")
        return None


# ─── Wizard inline (sin @st.dialog para garantizar cierre correcto) ───────────
def show_config_wizard():
    step = st.session_state.config_step

    # Encabezado con botón de cerrar arriba a la derecha
    h_col, cancel_col = st.columns([5, 1])
    with h_col:
        st.markdown("### ⚙️ Configurar búsqueda")
    with cancel_col:
        st.markdown('<div class="cancel-marker" style="height:0.55rem;"></div>', unsafe_allow_html=True)
        if st.button(
            "✕ Cerrar",
            use_container_width=True,
            key="wizard_cancel",
            help="Cierra el formulario y vuelve al inicio sin ejecutar ninguna búsqueda.",
        ):
            st.session_state.show_dialog = False
            st.rerun()

    _render_stepper(step)

    # ── Paso 1: Credenciales ──────────────────────────────────────────────
    if step == 1:
        with st.container(border=True):
            st.markdown("**🔑 Acceso a la IA**")
            with st.expander("¿Cómo obtengo la API key de Gemini?", icon="❓"):
                st.markdown("""
1. Ir a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Iniciar sesión con Google → **Create API Key**
3. Copiar la clave — es gratis, no requiere tarjeta.
""")
            st.session_state.gemini_key = st.text_input(
                "API Key de Gemini",
                value=st.session_state.gemini_key,
                type="password",
                placeholder="AIzaXXXXXXXXXXXXXXXXX",
            )
            _models = [
                "models/gemini-3.1-pro",
                "models/gemini-3.1-flash-lite",
                "models/gemini-3.0-flash",
                "models/gemini-2.5-pro",
                "models/gemini-2.5-flash",
                "models/gemini-2.5-flash-lite",
                "models/gemini-2.0-flash",
                "models/gemini-2.0-flash-lite",
                "models/gemini-1.5-pro",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-flash-8b",
            ]
            if st.session_state.selected_model not in _models:
                st.session_state.selected_model = "models/gemini-3.1-flash-lite"
            _idx = _models.index(st.session_state.selected_model)
            st.session_state.selected_model = st.selectbox("Modelo de IA", _models, index=_idx)

        with st.container(border=True):
            st.session_state.send_email = st.checkbox(
                "📧 Recibir resumen por email al terminar",
                value=st.session_state.send_email,
            )
            if st.session_state.send_email:
                with st.expander("¿Cómo obtengo la contraseña de app de Gmail?", icon="❓"):
                    st.markdown("""
1. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Verificación en 2 pasos **activada**
3. Crear app `Job Hunter` → copiar los 16 caracteres
""")
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.email_sender = st.text_input(
                        "Tu Gmail",
                        value=st.session_state.email_sender,
                        placeholder="tu@gmail.com",
                    )
                with c2:
                    st.session_state.email_recipient = st.text_input(
                        "Email destinatario",
                        value=st.session_state.email_recipient,
                        placeholder="destino@gmail.com",
                    )
                st.session_state.email_password_raw = st.text_input(
                    "Contraseña de app (16 caracteres)",
                    value=st.session_state.email_password_raw,
                    type="password",
                    placeholder="abcd efgh ijkl mnop",
                )

        if st.button("Siguiente →", type="primary", use_container_width=True):
            err = []
            if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
                err.append("API key inválida.")
            if st.session_state.send_email:
                if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
                    err.append("Email de envío inválido.")
                if len(st.session_state.email_password_raw.replace(" ", "")) != 16:
                    err.append("Contraseña de app: 16 caracteres.")
                if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
                    err.append("Email destinatario inválido.")
            if err:
                st.toast(" · ".join(err), icon="⚠️")
            else:
                st.session_state.config_step = 2
                st.rerun()

    # ── Paso 2: CV ────────────────────────────────────────────────────────
    elif step == 2:
        with st.container(border=True):
            st.markdown("**📄 Subí tu CV**")
            st.caption(
                "La IA extrae keywords y arma tu perfil automáticamente. "
                "Podés editarlos después o saltear este paso."
            )
            uploaded_file = st.file_uploader(
                "CV (PDF, DOCX o TXT)",
                type=["pdf", "docx", "txt"],
                label_visibility="collapsed",
                key="cv_upload",
            )
            if uploaded_file:
                if st.button("🤖 Analizar CV con IA", type="primary", use_container_width=True):
                    with st.spinner("Analizando tu CV…"):
                        result = _analyze_cv(
                            uploaded_file,
                            st.session_state.gemini_key,
                            st.session_state.selected_model,
                        )
                    if result:
                        kws  = [k for k in result.get("keywords", []) if k.strip()]
                        prof = result.get("profile", "").strip()
                        if kws:
                            st.session_state.keywords_list = kws
                            st.session_state["kw_tags"] = list(kws)
                        if prof:
                            st.session_state.candidate_profile = prof
                        st.session_state.cv_analyzed = True
                        st.toast(f"✅ {len(kws)} keywords extraídas. Revisalas en el paso siguiente.", icon="✅")
                    else:
                        st.toast("No se pudo analizar el CV. Continuá y completá los datos a mano.", icon="⚠️")

        if st.session_state.cv_analyzed:
            with st.container(border=True):
                st.markdown("**📋 Extraído de tu CV — revisá antes de continuar:**")
                kw_html = "".join(
                    f'<span style="display:inline-block;padding:3px 11px;margin:2px 3px;'
                    f'background:#ede9fe;color:#4f46e5;border-radius:20px;'
                    f'font-size:13px;font-weight:500;">{k}</span>'
                    for k in st.session_state.keywords_list
                )
                st.markdown(
                    f'<div style="margin:0.35rem 0 0.5rem 0;">{kw_html}</div>',
                    unsafe_allow_html=True,
                )
                st.caption("Perfil: " + st.session_state.candidate_profile[:220].replace("\n", " ") + "…")

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Atrás", use_container_width=True):
                st.session_state.config_step = 1
                st.rerun()
        with col_next:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                st.session_state.config_step = 3
                st.rerun()

    # ── Paso 3: Keywords y fuentes ────────────────────────────────────────
    elif step == 3:
        with st.container(border=True):
            st.markdown("**🔍 Keywords de búsqueda**")

            # Procesar keyword pendiente ANTES de instanciar el multiselect
            if "_pending_add" in st.session_state:
                _kw = st.session_state.pop("_pending_add")
                if _kw and _kw not in st.session_state.keywords_list:
                    st.session_state.keywords_list.append(_kw)
                st.session_state["kw_tags"] = list(st.session_state.keywords_list)

            if "kw_tags" not in st.session_state:
                st.session_state["kw_tags"] = list(st.session_state.keywords_list)

            _opts = list(st.session_state["kw_tags"])
            selected = st.multiselect(
                "Keywords",
                options=_opts,
                key="kw_tags",
                placeholder="Tus keywords — × para quitar",
                label_visibility="collapsed",
            )
            st.session_state.keywords_list = list(selected)

            with st.form("add_kw", clear_on_submit=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    new_kw = st.text_input(
                        "kw", placeholder="Agregar keyword...",
                        label_visibility="collapsed",
                    )
                with c2:
                    add_submitted = st.form_submit_button("+ Agregar", use_container_width=True)
                if add_submitted and new_kw.strip():
                    st.session_state["_pending_add"] = new_kw.strip()
                    st.rerun()

        with st.container(border=True):
            st.markdown("**⚙️ Parámetros**")
            st.session_state.min_score = st.slider(
                "Puntaje mínimo para recomendar",
                min_value=30, max_value=90, step=5,
                value=st.session_state.min_score,
                help="Las ofertas con puntaje menor quedan fuera de los resultados recomendados.",
            )
            st.markdown("**Fuentes**")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.session_state.use_remotive  = st.checkbox("Remotive",       value=st.session_state.use_remotive)
            with c2:
                st.session_state.use_arbeitnow = st.checkbox("Arbeitnow",      value=st.session_state.use_arbeitnow)
            with c3:
                st.session_state.use_wwr       = st.checkbox("WeWorkRemotely", value=st.session_state.use_wwr)
            with c4:
                st.session_state.use_himalayas = st.checkbox("Himalayas",      value=st.session_state.use_himalayas)

            st.session_state.use_max_results = st.checkbox(
                "Limitar cantidad de ofertas a analizar",
                value=st.session_state.use_max_results,
                help="Útil para pruebas rápidas o para ahorrar cuota de IA.",
            )
            if st.session_state.use_max_results:
                st.session_state.max_results_limit = st.slider(
                    "Máximo de ofertas", min_value=10, max_value=500, step=10,
                    value=st.session_state.max_results_limit,
                )

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Atrás", use_container_width=True):
                st.session_state.config_step = 2
                st.rerun()
        with col_next:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                if not st.session_state.keywords_list:
                    st.toast("Agregá al menos una keyword.", icon="⚠️")
                elif not any([st.session_state.use_remotive, st.session_state.use_arbeitnow,
                              st.session_state.use_wwr, st.session_state.use_himalayas]):
                    st.toast("Seleccioná al menos una fuente.", icon="⚠️")
                else:
                    st.session_state.config_step = 4
                    st.rerun()

    # ── Paso 4: Perfil ────────────────────────────────────────────────────
    elif step == 4:
        with st.container(border=True):
            st.markdown("**👤 Tu perfil profesional**")
            st.caption("La IA usa este texto para evaluar qué tan bien encaja cada oferta con vos.")
            st.session_state.candidate_profile = st.text_area(
                "perfil",
                value=st.session_state.candidate_profile,
                height=195,
                label_visibility="collapsed",
                placeholder="Rol buscado, stack técnico, experiencia, idiomas...",
            )

        col_back, col_start = st.columns(2)
        with col_back:
            if st.button("← Atrás", use_container_width=True):
                st.session_state.config_step = 3
                st.rerun()
        with col_start:
            if st.button("🚀 Iniciar búsqueda", type="primary", use_container_width=True):
                errors = validate_config()
                if errors:
                    st.toast(" · ".join(errors), icon="⚠️")
                else:
                    st.session_state.show_dialog = False
                    st.session_state.run_search  = True
                    st.rerun()  # rerun desde contexto principal — siempre full-page


# ─── Wizard (toma la pantalla completa cuando está activo) ────────────────────
if st.session_state.show_dialog:
    show_config_wizard()
    st.stop()

# ─── Título ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 1.75rem 0 0.75rem 0;">
    <div style="display:inline-flex; align-items:center; justify-content:center;
                width:60px; height:60px; border-radius:14px;
                background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
                box-shadow:0 8px 24px rgba(79,70,229,0.32);
                font-size:28px; margin-bottom:0.9rem;">🎯</div>
    <h1 style="font-size:2.1rem; font-weight:800; color:#0f172a;
               margin:0 0 0.45rem 0; letter-spacing:-0.03em; line-height:1.15;">
        Job Hunter <span style="color:#4f46e5;">AI</span>
    </h1>
    <p style="color:#64748b; font-size:1rem; margin:0 auto; max-width:480px; line-height:1.65;">
        Buscá ofertas remotas, priorizalas con IA y generá cartas de presentación listas para usar.
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Placeholders ─────────────────────────────────────────────────────────────
st.divider()
action_placeholder      = st.empty()
workflow_placeholder    = st.empty()
results_placeholder     = st.empty()
empty_state_placeholder = st.empty()


def render_empty_state():
    with empty_state_placeholder.container():
        st.markdown("""
<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin:1.5rem 0 0.5rem 0;">
    <div class="feature-card">
        <span class="feature-icon">🔍</span>
        <div class="feature-title">Busca</div>
        <div class="feature-desc">Remotive, Arbeitnow, WeWorkRemotely e Himalayas</div>
    </div>
    <div class="feature-card">
        <span class="feature-icon">🤖</span>
        <div class="feature-title">Analiza</div>
        <div class="feature-desc">La IA puntúa cada oferta del 0 al 100 según tu perfil</div>
    </div>
    <div class="feature-card">
        <span class="feature-icon">📝</span>
        <div class="feature-title">Redacta</div>
        <div class="feature-desc">Genera cartas de presentación personalizadas</div>
    </div>
    <div class="feature-card">
        <span class="feature-icon">📧</span>
        <div class="feature-title">Envía</div>
        <div class="feature-desc">Resumen por email al terminar (opcional)</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── Botón de acción ──────────────────────────────────────────────────────────
with action_placeholder.container():
    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        _label = "🔄 Nueva búsqueda" if st.session_state.search_done else "⚙️ Configurar y buscar"
        if st.button(_label, type="primary", use_container_width=True):
            st.session_state.show_dialog = True
            st.session_state.config_step = 1
            st.rerun()
        if not st.session_state.search_done and not st.session_state.run_search:
            st.info("⏱️ Una búsqueda completa suele tardar entre 6 y 8 minutos.")

if not st.session_state.run_search and not st.session_state.search_done:
    render_empty_state()

# ─── Ejecución de la búsqueda ─────────────────────────────────────────────────
if st.session_state.run_search:
    st.session_state.run_search = False
    empty_state_placeholder.empty()
    results_placeholder.empty()

    gemini_key        = st.session_state.gemini_key
    selected_model    = st.session_state.selected_model
    send_email        = st.session_state.send_email
    email_sender      = st.session_state.email_sender
    email_password    = st.session_state.email_password_raw.replace(" ", "")
    email_recipient   = st.session_state.email_recipient
    keywords          = list(st.session_state.keywords_list)
    min_score         = st.session_state.min_score
    max_results_limit = st.session_state.max_results_limit if st.session_state.use_max_results else 0
    candidate_profile = st.session_state.candidate_profile

    os.environ["GEMINI_API_KEY"]  = gemini_key
    os.environ["EMAIL_SENDER"]    = email_sender
    os.environ["EMAIL_PASSWORD"]  = email_password
    os.environ["EMAIL_RECIPIENT"] = email_recipient

    import config as cfg
    cfg.GEMINI_API_KEY    = gemini_key
    cfg.SEARCH_KEYWORDS   = keywords
    cfg.MIN_MATCH_SCORE   = min_score
    cfg.CANDIDATE_PROFILE = candidate_profile
    cfg.EMAIL_SENDER      = email_sender
    cfg.EMAIL_PASSWORD    = email_password
    cfg.EMAIL_RECIPIENT   = email_recipient

    import ai_engine
    ai_engine.MODEL = selected_model
    from google import genai as _genai
    ai_engine.client = _genai.Client(api_key=gemini_key)

    import scrapers as sc

    def render_workflow_step(step_number, step_title):
        with workflow_placeholder.container():
            with st.container(border=True):
                st.caption(f"Paso {step_number}  ·  {step_title}")
                status   = st.empty()
                notice   = st.empty()
                progress = st.empty()
                extra    = st.empty()
        return status, notice, progress, extra

    # ── STEP 1: Scraping ──────────────────────────────────────────────────────
    platform_status, platform_notice, progress_scrape, _ = render_workflow_step(1, "Buscar ofertas")
    progress_scrape.progress(0, text="Iniciando...")

    all_jobs    = []
    seen_global = set()
    platforms_enabled = {
        "Remotive":       st.session_state.use_remotive,
        "Arbeitnow":      st.session_state.use_arbeitnow,
        "WeWorkRemotely": st.session_state.use_wwr,
        "Himalayas":      st.session_state.use_himalayas,
    }
    enabled_list    = [p for p, v in platforms_enabled.items() if v]
    total_platforms = len(enabled_list)
    scrape_started  = time.monotonic()

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(f"Buscando en **{platform_name}**...")
        if max_results_limit > 0 and len(all_jobs) >= max_results_limit:
            break
        try:
            remaining = max_results_limit - len(all_jobs) if max_results_limit > 0 else 0
            if platform_name == "Remotive":
                jobs = sc.scrape_remotive(keywords, max_results=remaining)
            elif platform_name == "Arbeitnow":
                jobs = sc.scrape_arbeitnow(keywords, max_results=remaining)
            elif platform_name == "WeWorkRemotely":
                jobs = sc.scrape_weworkremotely(max_results=remaining)
            elif platform_name == "Himalayas":
                jobs = sc.scrape_himalayas(keywords, max_results=remaining)
            else:
                jobs = []
            for job in jobs:
                key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
                if key not in seen_global:
                    seen_global.add(key)
                    all_jobs.append(job)
                if max_results_limit > 0 and len(all_jobs) >= max_results_limit:
                    break
        except Exception as e:
            platform_notice.warning(f"⚠️ Error en {platform_name}: {e}")

        completed = idx + 1
        elapsed   = time.monotonic() - scrape_started
        rem_plat  = total_platforms - completed
        eta       = f"  ·  ~{format_duration((elapsed / completed) * rem_plat)} restantes" if rem_plat > 0 else ""
        progress_scrape.progress(completed / total_platforms, text=f"{completed}/{total_platforms} fuentes{eta}")

    platform_status.success(
        f"✅ **{len(all_jobs)} ofertas únicas** encontradas — {format_duration(time.monotonic() - scrape_started)}"
    )
    progress_scrape.progress(1.0)

    # ── STEP 2: AI Scoring ────────────────────────────────────────────────────
    ai_status, ai_notice, progress_ai, live_results = render_workflow_step(2, "Analizar con IA")

    scored_jobs    = []
    top_matches    = []
    quota_exceeded = False
    total_jobs     = len(all_jobs)

    if total_jobs == 0:
        ai_status.warning("No se encontraron ofertas para analizar.")
        progress_ai.progress(1.0)
    else:
        progress_ai.progress(0, text="Iniciando análisis...")
        scoring_started = time.monotonic()

        for i, job in enumerate(all_jobs):
            ai_status.info(f"Analizando **{i + 1}/{total_jobs}**: {job.title[:50]} @ {job.company}")
            data  = ai_engine.score_job(job)
            score = data.get("score", 0)
            if data.get("quota_exceeded", False):
                quota_exceeded = True
                ai_notice.error(f"Se agotó la cuota diaria de Gemini. Se analizaron {i} de {total_jobs} ofertas.")
                break

            from ai_engine import ScoredJob
            sj = ScoredJob(
                job=job, score=score,
                match_reasons=data.get("match_reasons", []),
                missing_skills=data.get("missing_skills", []),
                cover_letter=None,
                summary=data.get("summary", ""),
            )
            scored_jobs.append(sj)

            top5 = sorted(scored_jobs, key=lambda x: x.score, reverse=True)[:5]
            with live_results.container():
                st.caption("Mejores resultados hasta ahora:")
                for t in top5:
                    color = "score-high" if t.score >= 80 else "score-medium" if t.score >= 60 else "score-low"
                    st.markdown(
                        f'<span class="score-badge {color}">{t.score}/100</span> '
                        f'**{t.job.title}** @ {t.job.company}',
                        unsafe_allow_html=True,
                    )

            completed = i + 1
            elapsed   = time.monotonic() - scoring_started
            rem_jobs  = total_jobs - completed
            eta       = f"  ·  ~{format_duration((elapsed / completed) * rem_jobs)} restantes" if rem_jobs > 0 else ""
            progress_ai.progress(completed / total_jobs, text=f"{completed}/{total_jobs} analizadas{eta}")
            time.sleep(0.1)

        scored_jobs.sort(key=lambda x: x.score, reverse=True)
        top_matches = [j for j in scored_jobs if j.score >= min_score]
        if not quota_exceeded:
            ai_status.success(
                f"✅ **{len(top_matches)} recomendadas** de {len(scored_jobs)} analizadas"
                f" — {format_duration(time.monotonic() - scoring_started)}"
            )
        progress_ai.progress(1.0)

    # ── STEP 3: Cover Letters ─────────────────────────────────────────────────
    if top_matches:
        cl_status, _, progress_cl, _ = render_workflow_step(3, "Generar cartas")
        progress_cl.progress(0, text="Iniciando...")
        cover_started = time.monotonic()
        total_letters = len(top_matches)

        for i, sj in enumerate(top_matches):
            cl_status.info(f"Generando carta **{i + 1}/{total_letters}** — {sj.job.title}")
            sj.cover_letter = ai_engine.generate_cover_letter(sj.job, {"match_reasons": sj.match_reasons})
            completed = i + 1
            elapsed   = time.monotonic() - cover_started
            rem_let   = total_letters - completed
            eta       = f"  ·  ~{format_duration((elapsed / completed) * rem_let)} restantes" if rem_let > 0 else ""
            progress_cl.progress(completed / total_letters, text=f"{completed}/{total_letters} cartas{eta}")

        cl_status.success(
            f"✅ {total_letters} {'carta generada' if total_letters == 1 else 'cartas generadas'}"
            f" — {format_duration(time.monotonic() - cover_started)}"
        )
        progress_cl.progress(1.0)

    # ── STEP 4: Email ─────────────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        email_status, _, _, _ = render_workflow_step(4, "Enviar resumen por email")
        try:
            from notifier import send_digest
            cfg.EMAIL_SENDER    = email_sender
            cfg.EMAIL_PASSWORD  = email_password
            cfg.EMAIL_RECIPIENT = email_recipient
            email_status.info(f"Enviando resumen a {email_recipient}...")
            send_digest(scored_jobs)
            email_status.success(f"✅ Resumen enviado a **{email_recipient}**.")
        except Exception as e:
            email_status.error(f"No se pudo enviar el email: {e}")

    workflow_placeholder.empty()

    # ── Guardar resultados ────────────────────────────────────────────────────
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    ts          = datetime.now().strftime("%Y%m%d_%H%M")
    result_file = results_dir / f"results_{ts}.json"
    data_out    = [
        {
            "score":            sj.score,
            "title":            sj.job.title,
            "company":          sj.job.company,
            "source":           sj.job.source,
            "url":              sj.job.url,
            "match_reasons":    sj.match_reasons,
            "summary":          sj.summary,
            "has_cover_letter": sj.cover_letter is not None,
        }
        for sj in scored_jobs
    ]
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)

    st.session_state.search_done = True

    # ── Resultados ────────────────────────────────────────────────────────────
    with results_placeholder.container():
        st.header("📊 Resultados")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Analizadas",       len(scored_jobs))
        c2.metric("Recomendadas",     len(top_matches))
        c3.metric("Mejor puntaje",    f"{scored_jobs[0].score}/100" if scored_jobs else "—")
        c4.metric("Excelentes (80+)", sum(1 for j in scored_jobs if j.score >= 80))

        def render_job_card(sj, idx, section):
            score     = sj.score
            color     = "score-high" if score >= 80 else "score-medium" if score >= 60 else "score-low"
            src_class = {
                "Remotive":       "src-remotive",
                "Arbeitnow":      "src-arbeitnow",
                "WeWorkRemotely": "src-wwr",
                "Himalayas":      "src-himalayas",
            }.get(sj.job.source, "src-remotive")

            with st.expander(f"{score}/100 — {sj.job.title}  @  {sj.job.company}", expanded=(idx == 0)):
                header_col, link_col = st.columns([3, 1])
                with header_col:
                    st.markdown(
                        f'<span class="score-badge {color}">{score}/100</span> '
                        f'<span class="source-badge {src_class}">{sj.job.source}</span>',
                        unsafe_allow_html=True,
                    )
                    if sj.summary:
                        st.caption(sj.summary)
                with link_col:
                    if sj.job.url:
                        st.link_button("Abrir oferta", sj.job.url, use_container_width=True)

                r1, r2 = st.columns(2)
                with r1:
                    st.markdown("**✅ Por qué encaja con tu perfil**")
                    for reason in sj.match_reasons:
                        st.markdown(f"- {reason}")
                with r2:
                    st.markdown("**⚠️ Lo que podría faltar**")
                    if sj.missing_skills:
                        for skill in sj.missing_skills:
                            st.markdown(f"- {skill}")
                    else:
                        st.markdown("- Sin faltantes críticos")

                if sj.cover_letter:
                    st.markdown("**📝 Carta generada**")
                    st.markdown(f'<div class="cover-letter-box">{sj.cover_letter}</div>', unsafe_allow_html=True)
                    st.download_button(
                        "⬇ Descargar carta",
                        data=sj.cover_letter,
                        file_name=f"cover_{sj.job.company.replace(' ', '_')}_{sj.job.title[:20].replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"dl_{section}_{sj.job.id}_{idx}",
                    )

        top_tab, all_tab = st.tabs([
            f"🔥 Recomendadas ({len(top_matches)})",
            f"📋 Todas ({len(scored_jobs)})",
        ])
        with top_tab:
            if top_matches:
                for i, sj in enumerate(top_matches):
                    render_job_card(sj, i, "top")
            else:
                st.info(
                    f"Ninguna oferta superó el puntaje mínimo de {min_score}. "
                    f"Probá bajar el valor en la configuración."
                )
        with all_tab:
            st.caption("Ordenadas de mayor a menor puntaje.")
            for i, sj in enumerate(scored_jobs):
                render_job_card(sj, i, "all")

        st.download_button(
            "⬇ Descargar resultados completos (JSON)",
            data=json.dumps(data_out, ensure_ascii=False, indent=2),
            file_name=f"job_hunt_{ts}.json",
            mime="application/json",
        )
