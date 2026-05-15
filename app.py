"""
app.py — Job Hunter UI con Streamlit
"""

import streamlit as st
import json
import time
import os
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="Job Hunter AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
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
    /* Make the keyword add-form blend with the multiselect above it */
    div[data-testid="stDialog"] div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
    }
    .cover-letter-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        font-family: Georgia, serif;
        font-size: 14px;
        line-height: 1.8;
        white-space: pre-wrap;
    }
    .workflow-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 18px 18px 10px 18px;
        margin-bottom: 16px;
    }
    div[data-testid="stExpander"] { border: 1px solid #e2e8f0; border-radius: 8px; }
    section[data-testid="stSidebar"] { display: none; }
    button[data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ─── Session state defaults ───────────────────────────────────────────────────
_defaults = {
    "show_dialog":        False,
    "config_step":        1,
    "run_search":         False,
    "search_done":        False,
    "gemini_key":         "",
    "selected_model":     "models/gemini-2.5-flash",
    "send_email":         False,
    "email_sender":       "",
    "email_password_raw": "",
    "email_recipient":    "",
    "keywords_list":      ["frontend developer", "react developer", "full stack engineer", "UI engineer", "javascript developer"],
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


# ─── Dialog ───────────────────────────────────────────────────────────────────
@st.dialog("⚙️ Configurar búsqueda", width="large")
def config_dialog():
    step = st.session_state.config_step
    st.progress(step / 3, text=f"Paso {step} de 3")
    st.divider()

    # ── Paso 1: Credenciales ──────────────────────────────────────────────────
    if step == 1:
        st.subheader("🔑 Credenciales")

        with st.expander("¿Cómo obtengo la API key de Gemini?", icon="❓"):
            st.markdown("""
1. Ir a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Iniciar sesión con Google → **Create API Key**
3. Copiar la clave — es gratis, no requiere tarjeta.
""")

        st.session_state.gemini_key = st.text_input(
            "API Key de Gemini", value=st.session_state.gemini_key,
            type="password", placeholder="AIzaXXXXXXXXXXXXXXXXX",
        )

        _models = [
            "models/gemini-2.5-flash", "models/gemini-2.5-flash-lite",
            "models/gemini-2.0-flash-lite", "models/gemini-3.1-flash-lite", "models/gemini-3.1-pro",
        ]
        _idx = _models.index(st.session_state.selected_model) if st.session_state.selected_model in _models else 0
        st.session_state.selected_model = st.selectbox("Modelo", _models, index=_idx)

        st.divider()
        st.session_state.send_email = st.checkbox("📧 Recibir resumen por email", value=st.session_state.send_email)
        if st.session_state.send_email:
            with st.expander("¿Cómo obtengo la contraseña de aplicación de Gmail?", icon="❓"):
                st.markdown("""
1. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Verificación en 2 pasos **activada**
3. Crear app `Job Hunter` → copiar los 16 caracteres
""")
            st.session_state.email_sender = st.text_input(
                "Email de envío", value=st.session_state.email_sender, placeholder="tu@gmail.com",
            )
            st.session_state.email_password_raw = st.text_input(
                "Contraseña de app (16 caracteres)", value=st.session_state.email_password_raw,
                type="password", placeholder="abcd efgh ijkl mnop",
            )
            st.session_state.email_recipient = st.text_input(
                "Email destinatario", value=st.session_state.email_recipient, placeholder="tu@gmail.com",
            )

        st.markdown("")
        if st.button("Siguiente →", type="primary", use_container_width=True):
            err = []
            if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
                err.append("API key inválida.")
            if st.session_state.send_email:
                pw = st.session_state.email_password_raw.replace(" ", "")
                if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
                    err.append("Email de envío inválido.")
                if len(pw) != 16:
                    err.append("La contraseña de app debe tener 16 caracteres.")
                if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
                    err.append("Email destinatario inválido.")
            if err:
                st.toast(" · ".join(err), icon="⚠️")
            else:
                st.session_state.config_step = 2
                st.rerun()

    # ── Paso 2: Búsqueda y fuentes ────────────────────────────────────────────
    elif step == 2:
        st.subheader("🔍 Búsqueda")

        # Procesar keyword pendiente de agregar ANTES de renderizar el multiselect
        if "_pending_add" in st.session_state:
            _kw = st.session_state.pop("_pending_add")
            if _kw and _kw not in st.session_state.keywords_list:
                st.session_state.keywords_list.append(_kw)
            # Pre-cargar el valor del multiselect con la lista actualizada
            st.session_state["kw_tags"] = list(st.session_state.keywords_list)

        # Inicializar el multiselect si todavía no existe
        if "kw_tags" not in st.session_state:
            st.session_state["kw_tags"] = list(st.session_state.keywords_list)

        # Multiselect = tags nativos de Streamlit con × integrado
        # options = kw_tags (el estado actual del widget, sin ítems eliminados)
        _opts = list(st.session_state["kw_tags"])
        selected = st.multiselect(
            "Keywords",
            options=_opts,
            default=_opts,
            key="kw_tags",
            placeholder="Tus keywords aparecen acá — × para quitar",
            label_visibility="collapsed",
        )
        # Sincronizar keywords_list con lo que el usuario haya quitado
        st.session_state.keywords_list = list(selected)

        # Formulario para agregar (Enter o botón)
        with st.form("add_kw", clear_on_submit=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                new_kw = st.text_input(
                    "kw", placeholder="Nueva keyword — Enter para agregar",
                    label_visibility="collapsed",
                )
            with c2:
                add_submitted = st.form_submit_button("+ Agregar", use_container_width=True)
            if add_submitted and new_kw.strip():
                # Guardar en pendiente: se procesa al inicio del próximo render,
                # ANTES de que el multiselect se instancie (evita el error de key)
                st.session_state["_pending_add"] = new_kw.strip()
                st.rerun()

        st.divider()

        st.session_state.min_score = st.slider(
            "Puntaje mínimo", min_value=30, max_value=90,
            value=st.session_state.min_score, step=5,
            help="Ofertas por debajo de este puntaje no aparecen en los resultados.",
        )

        st.markdown("**Fuentes**")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.use_remotive  = st.checkbox("Remotive",       value=st.session_state.use_remotive)
            st.session_state.use_arbeitnow = st.checkbox("Arbeitnow",      value=st.session_state.use_arbeitnow)
        with c2:
            st.session_state.use_wwr       = st.checkbox("WeWorkRemotely", value=st.session_state.use_wwr)
            st.session_state.use_himalayas = st.checkbox("Himalayas",      value=st.session_state.use_himalayas)

        st.session_state.use_max_results = st.checkbox(
            "Limitar cantidad de ofertas",
            value=st.session_state.use_max_results,
            help="Útil para pruebas rápidas o para ahorrar cuota de IA.",
        )
        if st.session_state.use_max_results:
            st.session_state.max_results_limit = st.slider(
                "Máximo de ofertas", min_value=10, max_value=1000,
                value=st.session_state.max_results_limit, step=10,
            )

        st.markdown("")
        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Atrás", use_container_width=True):
                st.session_state.config_step = 1
                st.rerun()
        with col_next:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                if not st.session_state.keywords_list:
                    st.toast("Agregá al menos una keyword.", icon="⚠️")
                elif not any([st.session_state.use_remotive, st.session_state.use_arbeitnow,
                              st.session_state.use_wwr, st.session_state.use_himalayas]):
                    st.toast("Seleccioná al menos una fuente.", icon="⚠️")
                else:
                    st.session_state.config_step = 3
                    st.rerun()

    # ── Paso 3: Perfil ────────────────────────────────────────────────────────
    elif step == 3:
        st.subheader("👤 Perfil profesional")

        st.session_state.candidate_profile = st.text_area(
            "perfil",
            value=st.session_state.candidate_profile,
            height=290,
            label_visibility="collapsed",
            placeholder="Rol buscado, stack técnico, experiencia, idiomas...",
        )

        st.markdown("")
        col_back, col_start = st.columns(2)
        with col_back:
            if st.button("← Atrás", use_container_width=True):
                st.session_state.config_step = 2
                st.rerun()
        with col_start:
            if st.button("🚀 Iniciar búsqueda", type="primary", use_container_width=True):
                errors = validate_config()
                if errors:
                    st.toast(" · ".join(errors), icon="⚠️")
                else:
                    st.session_state.show_dialog = False
                    st.session_state.run_search  = True
                    st.rerun(scope="app")


# ─── Main area ────────────────────────────────────────────────────────────────
st.title("🎯 Job Hunter AI")
st.caption("Buscá ofertas remotas, priorizalas con IA y generá cartas listas para usar.")

if st.session_state.show_dialog:
    config_dialog()

action_placeholder      = st.empty()
workflow_placeholder    = st.empty()
results_placeholder     = st.empty()
empty_state_placeholder = st.empty()


def format_duration(seconds):
    seconds = max(0, int(round(seconds)))
    minutes, secs = divmod(seconds, 60)
    if minutes:
        return f"{minutes} min {secs:02d} s"
    return f"{secs} s"


def render_empty_state():
    with empty_state_placeholder.container():
        st.markdown("""
### Hacé click en **Configurar y buscar** para empezar

**¿Qué hace esta app?**
1. Busca ofertas remotas en Remotive, Arbeitnow, WeWorkRemotely e Himalayas
2. Analiza cada oferta con IA según tu perfil (puntaje 0–100)
3. Genera cartas de presentación personalizadas
4. Opcional: envía un resumen por email al finalizar
""")
        st.info("💡 Podés usar la app sin email y ver todos los resultados en pantalla.")


# ─── Botón de acción ──────────────────────────────────────────────────────────
with action_placeholder.container():
    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        _label = "🔄 Nueva búsqueda" if st.session_state.search_done else "⚙️ Configurar y buscar"
        if st.button(_label, type="primary", use_container_width=True):
            st.session_state.show_dialog = True
            st.session_state.config_step = 1
            st.rerun()
    with col_info:
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

    def render_workflow_step(step_number, step_title, step_description):
        with workflow_placeholder.container():
            st.markdown('<div class="workflow-card">', unsafe_allow_html=True)
            st.caption(f"Paso actual: {step_number} de 4")
            st.subheader(step_title)
            st.caption(step_description)
            status   = st.empty()
            notice   = st.empty()
            eta      = st.empty()
            progress = st.empty()
            extra    = st.empty()
            st.markdown("</div>", unsafe_allow_html=True)
        return status, notice, eta, progress, extra

    # ── STEP 1: Scraping ──────────────────────────────────────────────────────
    platform_status, platform_notice, platform_eta, progress_scrape, _ = render_workflow_step(
        1, "Paso 1: buscar ofertas",
        "Estamos recorriendo las fuentes seleccionadas para reunir oportunidades relevantes.",
    )
    progress_scrape.progress(0)

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
    scrape_started_at = time.monotonic()

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(f"Buscando ofertas en **{platform_name}**...")
        if max_results_limit > 0 and len(all_jobs) >= max_results_limit:
            platform_status.success(f"✅ Se alcanzó el límite de {max_results_limit} ofertas.")
            platform_eta.info("Tiempo restante estimado: 0 s")
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
            platform_notice.warning(f"⚠️ Hubo un problema al consultar {platform_name}: {e}")

        completed = idx + 1
        progress_scrape.progress(completed / total_platforms)
        elapsed = time.monotonic() - scrape_started_at
        eta_sec = (elapsed / completed) * (total_platforms - completed)
        platform_eta.info(f"Tiempo restante estimado: {format_duration(eta_sec)}")

    platform_status.success(f"✅ Búsqueda terminada: **{len(all_jobs)} ofertas únicas** encontradas.")
    platform_eta.info(f"Tiempo total: {format_duration(time.monotonic() - scrape_started_at)}")

    # ── STEP 2: AI Scoring ────────────────────────────────────────────────────
    ai_status, ai_notice, ai_eta, progress_ai, live_results = render_workflow_step(
        2, "Paso 2: analizar cada oferta con IA",
        "Ahora evaluamos qué tan bien encaja cada oferta con tu perfil.",
    )
    progress_ai.progress(0)

    scored_jobs    = []
    quota_exceeded = False
    scoring_started_at = time.monotonic()
    total_jobs = len(all_jobs)

    for i, job in enumerate(all_jobs):
        ai_status.info(f"Analizando oferta **{i+1} de {total_jobs}**: {job.title[:50]} @ {job.company}")
        data  = ai_engine.score_job(job)
        score = data.get("score", 0)
        if data.get("quota_exceeded", False):
            quota_exceeded = True
            ai_notice.error(f"⚠️ Se agotó la cuota diaria de Gemini. Se evaluaron {i} ofertas. Podés continuar mañana.")
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
            st.caption("Mejores resultados hasta este momento:")
            for t in top5:
                color = "score-high" if t.score >= 80 else "score-medium" if t.score >= 60 else "score-low"
                st.markdown(
                    f'<span class="score-badge {color}">{t.score}/100</span> '
                    f'**{t.job.title}** @ {t.job.company}',
                    unsafe_allow_html=True,
                )

        completed = i + 1
        progress_ai.progress(completed / total_jobs)
        elapsed = time.monotonic() - scoring_started_at
        eta_sec = (elapsed / completed) * (total_jobs - completed)
        ai_eta.info(f"Tiempo restante estimado: {format_duration(eta_sec)}")
        time.sleep(0.1)

    scored_jobs.sort(key=lambda x: x.score, reverse=True)
    top_matches = [j for j in scored_jobs if j.score >= min_score]
    if not quota_exceeded:
        ai_status.success(f"✅ Análisis terminado: **{len(top_matches)} ofertas** superan el puntaje mínimo de {min_score}.")
        ai_eta.info(f"Tiempo total: {format_duration(time.monotonic() - scoring_started_at)}")

    # ── STEP 3: Cover Letters ─────────────────────────────────────────────────
    if top_matches:
        cl_status, _, cl_eta, progress_cl, _ = render_workflow_step(
            3, "Paso 3: generar cartas personalizadas",
            "Estamos preparando una carta para cada oportunidad recomendada.",
        )
        progress_cl.progress(0)
        cover_started_at = time.monotonic()
        total_letters = len(top_matches)

        for i, sj in enumerate(top_matches):
            cl_status.info(f"Generando carta **{i+1} de {total_letters}** para {sj.job.title}")
            sj.cover_letter = ai_engine.generate_cover_letter(sj.job, {"match_reasons": sj.match_reasons})
            completed = i + 1
            progress_cl.progress(completed / total_letters)
            elapsed = time.monotonic() - cover_started_at
            eta_sec = (elapsed / completed) * (total_letters - completed)
            cl_eta.info(f"Tiempo restante estimado: {format_duration(eta_sec)}")

        cl_status.success("✅ Cartas generadas.")
        cl_eta.info(f"Tiempo total: {format_duration(time.monotonic() - cover_started_at)}")

    # ── STEP 4: Email ─────────────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        email_status, _, email_eta, _, _ = render_workflow_step(
            4, "Paso 4: enviar resumen por email",
            "Último paso: enviamos el resumen con las mejores oportunidades.",
        )
        try:
            from notifier import send_digest
            cfg.EMAIL_SENDER    = email_sender
            cfg.EMAIL_PASSWORD  = email_password
            cfg.EMAIL_RECIPIENT = email_recipient
            email_status.info("Enviando resumen...")
            email_eta.info("Tiempo estimado: menos de 1 minuto")
            send_digest(scored_jobs)
            email_status.success(f"✅ Resumen enviado a **{email_recipient}**.")
            email_eta.info("Tiempo restante estimado: 0 s")
        except Exception as e:
            email_status.error(f"❌ No se pudo enviar el email: {e}")

    workflow_placeholder.empty()

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    result_file = results_dir / f"results_{ts}.json"
    data_out = [
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
        st.caption("Revisá las mejores oportunidades y descargá las cartas o el resumen completo.")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ofertas analizadas",   len(scored_jobs))
        c2.metric("Ofertas recomendadas", len(top_matches))
        c3.metric(
            "Mejor puntaje",
            f"{scored_jobs[0].score}/100" if scored_jobs else "—",
            scored_jobs[0].job.title[:30] if scored_jobs else "",
        )
        c4.metric("Muy buenas (80+)", sum(1 for j in scored_jobs if j.score >= 80))

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
                        st.markdown("- No hay faltantes críticos")

                if sj.cover_letter:
                    st.markdown("**📝 Carta generada**")
                    st.markdown(f'<div class="cover-letter-box">{sj.cover_letter}</div>', unsafe_allow_html=True)
                    st.download_button(
                        "⬇ Descargar carta",
                        data=sj.cover_letter,
                        file_name=f"cover_{sj.job.company.replace(' ','_')}_{sj.job.title[:20].replace(' ','_')}.txt",
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
                st.info(f"No se encontraron ofertas por encima de {min_score} puntos. Probá bajar el puntaje mínimo.")
        with all_tab:
            st.caption("Listado completo, ordenado de mayor a menor puntaje.")
            for i, sj in enumerate(scored_jobs):
                render_job_card(sj, i, "all")

        st.download_button(
            "⬇ Descargar resultados en JSON",
            data=json.dumps(data_out, ensure_ascii=False, indent=2),
            file_name=f"job_hunt_{ts}.json",
            mime="application/json",
        )
