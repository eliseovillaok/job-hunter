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

        st.text_input(
            "API Key de Gemini", key="gemini_key",
            type="password", placeholder="AIzaXXXXXXXXXXXXXXXXX",
        )

        _models = [
            "models/gemini-2.5-flash", "models/gemini-2.5-flash-lite",
            "models/gemini-2.0-flash-lite",
        ]
        if st.session_state.selected_model not in _models:
            st.session_state.selected_model = _models[0]
        st.selectbox("Modelo de IA", _models, key="selected_model")

        st.divider()
        st.checkbox("📧 Recibir resumen por email al terminar", key="send_email")
        if st.session_state.send_email:
            with st.expander("¿Cómo obtengo la contraseña de aplicación de Gmail?", icon="❓"):
                st.markdown("""
1. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Verificación en 2 pasos **activada**
3. Crear app `Job Hunter` → copiar los 16 caracteres
""")
            st.text_input("Tu Gmail", key="email_sender", placeholder="tu@gmail.com")
            st.text_input(
                "Contraseña de app (16 caracteres)", key="email_password_raw",
                type="password", placeholder="abcd efgh ijkl mnop",
            )
            st.text_input("Email donde recibir resultados", key="email_recipient", placeholder="tu@gmail.com")

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

    # ── Paso 2: Keywords y fuentes ────────────────────────────────────────────
    elif step == 2:
        st.subheader("🔍 Búsqueda")

        # Procesar keyword pendiente ANTES de que el multiselect se instancie
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
            default=_opts,
            key="kw_tags",
            placeholder="Tus keywords — × para quitar",
            label_visibility="collapsed",
        )
        st.session_state.keywords_list = list(selected)

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
                st.session_state["_pending_add"] = new_kw.strip()
                st.rerun()

        st.divider()

        st.slider(
            "Puntaje mínimo para recomendar", min_value=30, max_value=90, step=5,
            key="min_score",
            help="Las ofertas con puntaje menor a este valor quedan fuera de los resultados recomendados.",
        )

        st.markdown("**Fuentes donde buscar**")
        c1, c2 = st.columns(2)
        with c1:
            st.checkbox("Remotive",       key="use_remotive")
            st.checkbox("Arbeitnow",      key="use_arbeitnow")
        with c2:
            st.checkbox("WeWorkRemotely", key="use_wwr")
            st.checkbox("Himalayas",      key="use_himalayas")

        st.checkbox(
            "Limitar cantidad de ofertas a analizar",
            key="use_max_results",
            help="Útil para pruebas rápidas o para ahorrar cuota de IA.",
        )
        if st.session_state.use_max_results:
            st.slider("Máximo de ofertas", min_value=10, max_value=500, step=10, key="max_results_limit")

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
        st.subheader("👤 Tu perfil profesional")
        st.caption("La IA usa este texto para evaluar qué tan bien encaja cada oferta con vos.")

        st.text_area(
            "perfil",
            height=270,
            label_visibility="collapsed",
            placeholder="Rol buscado, stack técnico, experiencia, idiomas...",
            key="candidate_profile",
        )

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
4. Opcional: te envía un resumen por email al finalizar
""")
        st.info("💡 No necesitás configurar el email — podés ver todos los resultados directo en pantalla.")


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
        if not st.session_state.search_done and not st.session_state.run_search:
            st.caption("⏱️ Una búsqueda completa tarda entre 6 y 8 minutos.")

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
    platform_status, platform_notice, progress_scrape, _ = render_workflow_step(
        1, "Buscar ofertas",
    )
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
    scrape_started_at = time.monotonic()

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
        elapsed   = time.monotonic() - scrape_started_at
        remaining_platforms = total_platforms - completed
        eta_text  = f"  ·  ~{format_duration((elapsed / completed) * remaining_platforms)} restantes" if remaining_platforms > 0 else ""
        progress_scrape.progress(
            completed / total_platforms,
            text=f"{completed}/{total_platforms} fuentes{eta_text}",
        )

    scrape_elapsed = time.monotonic() - scrape_started_at
    platform_status.success(f"✅ **{len(all_jobs)} ofertas únicas** encontradas — {format_duration(scrape_elapsed)}")
    progress_scrape.progress(1.0)

    # ── STEP 2: AI Scoring ────────────────────────────────────────────────────
    ai_status, ai_notice, progress_ai, live_results = render_workflow_step(
        2, "Analizar con IA",
    )

    scored_jobs    = []
    top_matches    = []
    quota_exceeded = False
    total_jobs     = len(all_jobs)

    if total_jobs == 0:
        ai_status.warning("No se encontraron ofertas para analizar.")
        progress_ai.progress(1.0)
    else:
        progress_ai.progress(0, text="Iniciando análisis...")
        scoring_started_at = time.monotonic()

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
            elapsed   = time.monotonic() - scoring_started_at
            remaining_jobs = total_jobs - completed
            eta_text  = f"  ·  ~{format_duration((elapsed / completed) * remaining_jobs)} restantes" if remaining_jobs > 0 else ""
            progress_ai.progress(
                completed / total_jobs,
                text=f"{completed}/{total_jobs} analizadas{eta_text}",
            )
            time.sleep(0.1)

        scoring_elapsed = time.monotonic() - scoring_started_at
        scored_jobs.sort(key=lambda x: x.score, reverse=True)
        top_matches = [j for j in scored_jobs if j.score >= min_score]
        if not quota_exceeded:
            ai_status.success(
                f"✅ **{len(top_matches)} recomendadas** de {len(scored_jobs)} analizadas — {format_duration(scoring_elapsed)}"
            )
        progress_ai.progress(1.0)

    # ── STEP 3: Cover Letters ─────────────────────────────────────────────────
    if top_matches:
        cl_status, _, progress_cl, _ = render_workflow_step(3, "Generar cartas")
        progress_cl.progress(0, text="Iniciando...")
        cover_started_at = time.monotonic()
        total_letters    = len(top_matches)

        for i, sj in enumerate(top_matches):
            cl_status.info(f"Generando carta **{i + 1}/{total_letters}** — {sj.job.title}")
            sj.cover_letter = ai_engine.generate_cover_letter(sj.job, {"match_reasons": sj.match_reasons})
            completed = i + 1
            elapsed   = time.monotonic() - cover_started_at
            remaining_letters = total_letters - completed
            eta_text  = f"  ·  ~{format_duration((elapsed / completed) * remaining_letters)} restantes" if remaining_letters > 0 else ""
            progress_cl.progress(
                completed / total_letters,
                text=f"{completed}/{total_letters} cartas{eta_text}",
            )

        cover_elapsed = time.monotonic() - cover_started_at
        cl_status.success(
            f"✅ {total_letters} {'carta generada' if total_letters == 1 else 'cartas generadas'} — {format_duration(cover_elapsed)}"
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
        c1.metric("Analizadas", len(scored_jobs))
        c2.metric("Recomendadas", len(top_matches))
        c3.metric("Mejor puntaje", f"{scored_jobs[0].score}/100" if scored_jobs else "—")
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
                st.info(f"Ninguna oferta superó el puntaje mínimo de {min_score}. Probá bajar el valor en la configuración.")
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
