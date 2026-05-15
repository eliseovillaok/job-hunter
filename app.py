"""
app.py — Job Hunter UI con Streamlit
Interfaz web para configurar y correr el job hunter sin tocar código
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import time
import os
from datetime import datetime
from pathlib import Path

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Hunter AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Estilos custom ──────────────────────────────────────────────────────────
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
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .workflow-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 18px 18px 10px 18px;
        margin-bottom: 16px;
    }
    .results-anchor {
        display: block;
        position: relative;
        top: -12px;
    }
    div[data-testid="stExpander"] { border: 1px solid #e2e8f0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar: Configuración ──────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Job Hunter AI")
    st.caption("Configurá tu búsqueda laboral y recibí ofertas recomendadas con IA.")

    st.divider()

    # ── Credenciales ──────────────────────────────────────────────────────────
    st.header("🔑 Accesos")

    with st.expander("¿Cómo obtengo la API key de Gemini?", icon="❓"):
        st.markdown("""
1. Ir a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Iniciar sesión con Google
3. Hacer click en **Create API Key**
4. Copiar la clave (empieza con `AIza...`)

Es **gratis** y no necesitás tarjeta.
        """)

    gemini_key = st.text_input(
        "API Key de Gemini",
        type="password",
        placeholder="AIzaXXXXXXXXXXXXXXXXX",
        help="Pegá acá tu clave de Gemini.",
    )

    # Selector de modelo dinámico
    available_models = [
        "models/gemini-3.1-flash-lite",
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
        "models/gemini-3.1-pro",
    ]
    selected_model = st.selectbox(
        "Modelo",
        available_models,
        index=0,
        help="Elegí el modelo que querés usar para evaluar las ofertas.",
    )

    st.divider()

    # ── Email (OPCIONAL) ────────────────────────────────────────────────────────
    # Inicializar variables de email (por si no se tilda el checkbox)
    email_sender = ""
    email_password = ""
    email_recipient = ""
    
    send_email = st.checkbox("📧 Enviarme un resumen por email al finalizar", value=False)

    if send_email:
        with st.expander("¿Cómo obtengo la contraseña de aplicación de Gmail?", icon="❓"):
            st.markdown("""
1. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. La verificación en 2 pasos debe estar **activada**
3. En "Nombre de la app" escribir `Job Hunter`
4. Hacer click en **Crear** y copiar los 16 caracteres
5. Pegarlos abajo; si tienen espacios, se eliminan automáticamente

⚠️ **No** uses tu contraseña normal de Gmail.
            """)

        email_sender = st.text_input(
            "Email desde el que se envía",
            placeholder="tu@gmail.com",
        )
        email_password_raw = st.text_input(
            "Contraseña de aplicación (16 caracteres)",
            type="password",
            placeholder="abcd efgh ijkl mnop",
            help="Se eliminarán automáticamente los espacios",
        )
        email_password = email_password_raw.replace(" ", "")
        email_recipient = st.text_input(
            "Email que recibe el resumen",
            placeholder="tu@gmail.com",
            help="Puede ser el mismo email de envío u otro distinto.",
        )
    
    st.divider()

    # ── Búsqueda ───────────────────────────────────────────────────────────────
    st.header("🔍 Búsqueda")

    keywords_raw = st.text_area(
        "Puestos o palabras clave",
        value="frontend developer\nreact developer\nfull stack engineer\nUI engineer\njavascript developer",
        height=120,
        help="Escribí una búsqueda por línea. Ejemplo: `frontend developer` o `react developer`.",
    )

    min_score = st.slider(
        "Puntaje mínimo para considerar una oferta interesante",
        min_value=30,
        max_value=90,
        value=65,
        step=5,
        help="Las ofertas por debajo de este puntaje quedan fuera del resumen y de los mejores resultados.",
    )

    st.subheader("⚙️ Límite opcional")
    use_max_results = st.checkbox(
        "Detener la búsqueda después de cierta cantidad de ofertas",
        value=False,
        help="Útil para pruebas rápidas o para gastar menos cuota de IA.",
    )
    max_results_limit = 0
    if use_max_results:
        max_results_limit = st.slider(
            "Cantidad máxima de ofertas",
            min_value=10,
            max_value=1000,
            value=100,
            step=10,
            help="La app deja de buscar cuando alcanza este número.",
        )

    st.subheader("Fuentes")
    col1, col2 = st.columns(2)
    with col1:
        use_remotive   = st.checkbox("Remotive",       value=True)
        use_arbeitnow  = st.checkbox("Arbeitnow",      value=True)
    with col2:
        use_wwr        = st.checkbox("WeWorkRemotely", value=True)
        use_himalayas  = st.checkbox("Himalayas",      value=True)

    st.divider()

    # ── Perfil del candidato ───────────────────────────────────────────────────
    st.header("👤 Perfil profesional")
    candidate_profile = st.text_area(
        "Contale a la IA qué tipo de perfil tenés",
        value="""Rol buscado: Frontend Engineer / Full Stack (solo remoto)

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
        height=200,
    )


# ─── Main area ───────────────────────────────────────────────────────────────
st.title("🎯 Job Hunter AI")
st.caption("Buscá ofertas remotas, priorizalas con IA y generá cartas listas para usar.")
results_placeholder = st.empty()
action_placeholder = st.empty()
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
### 👈 Completá la barra lateral y después hacé click en **Empezar búsqueda**

**¿Qué hace esta app por vos?**
1. Busca ofertas remotas en Remotive, Arbeitnow, WeWorkRemotely e Himalayas
2. Analiza cada oferta con IA según tu perfil y le da un puntaje de 0 a 100
3. Genera cartas personalizadas para las oportunidades con mejor encaje
4. Si querés, te envía un resumen por email al finalizar

**Qué necesitás para usarla**
- Una API key de Gemini (gratis en [aistudio.google.com](https://aistudio.google.com/app/apikey))
- Una contraseña de aplicación de Gmail, solo si querés recibir el resumen por email
        """)

        st.info("💡 Podés usar la app sin email y ver todos los resultados directamente en pantalla.")

# Validación antes de correr
def validate_config():
    errors = []
    if not gemini_key or not gemini_key.startswith("AIza"):
        errors.append("❌ Cargá una API key de Gemini válida.")
    
    if send_email:
        if not email_sender or "@" not in email_sender:
            errors.append("❌ Si querés enviar el resumen por email, completá el email de envío.")
        if not email_password or len(email_password.replace(" ","")) != 16:
            errors.append("❌ La contraseña de aplicación de Gmail debe tener exactamente 16 caracteres.")
        if not email_recipient or "@" not in email_recipient:
            errors.append("❌ Completá el email que va a recibir el resumen.")
    
    keywords = [k.strip() for k in keywords_raw.strip().splitlines() if k.strip()]
    if not keywords:
        errors.append("❌ Escribí al menos una búsqueda o palabra clave.")
    
    platforms = any([use_remotive, use_arbeitnow, use_wwr, use_himalayas])
    if not platforms:
        errors.append("❌ Seleccioná al menos una fuente de ofertas.")
    
    return errors

# ─── Run button ───────────────────────────────────────────────────────────────
with action_placeholder.container():
    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        run_button = st.button("🚀 Empezar búsqueda", type="primary", use_container_width=True)
    with col_info:
        st.info("⏱️ Una búsqueda completa suele tardar entre 6 y 8 minutos.")

render_empty_state()

if run_button:
    # Re-leer valores actuales de la UI (sin necesidad de Ctrl+Enter)
    # Streamlit actualiza automáticamente cuando haces click en el botón
    errors = validate_config()
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    keywords = [k.strip() for k in keywords_raw.strip().splitlines() if k.strip()]

    # Inyectar config en el entorno para que los módulos la usen
    os.environ["GEMINI_API_KEY"]    = gemini_key
    os.environ["EMAIL_SENDER"]      = email_sender or ""
    os.environ["EMAIL_PASSWORD"]    = email_password or ""
    os.environ["EMAIL_RECIPIENT"]   = email_recipient or ""

    # Parchear config dinámicamente
    import config as cfg
    cfg.GEMINI_API_KEY    = gemini_key
    cfg.SEARCH_KEYWORDS   = keywords
    cfg.MIN_MATCH_SCORE   = min_score
    cfg.CANDIDATE_PROFILE = candidate_profile
    cfg.EMAIL_SENDER      = email_sender or ""
    cfg.EMAIL_PASSWORD    = email_password or ""
    cfg.EMAIL_RECIPIENT   = email_recipient or ""

    # Parchear modelo en ai_engine
    import ai_engine
    ai_engine.MODEL  = selected_model
    from google import genai as _genai
    ai_engine.client = _genai.Client(api_key=gemini_key)

    # Parchear plataformas activas en scrapers
    import scrapers as sc

    workflow_placeholder = st.empty()

    def render_workflow_step(step_number, step_title, step_description):
        with workflow_placeholder.container():
            st.markdown('<div class="workflow-card">', unsafe_allow_html=True)
            st.caption(f"Paso actual: {step_number} de 4")
            st.subheader(step_title)
            st.caption(step_description)
            status = st.empty()
            notice = st.empty()
            eta = st.empty()
            progress = st.empty()
            extra = st.empty()
            st.markdown("</div>", unsafe_allow_html=True)
            return status, notice, eta, progress, extra

    # ── STEP 1: Scraping ───────────────────────────────────────────────────────
    platform_status, platform_notice, platform_eta, progress_scrape, _ = render_workflow_step(
        1,
        "Paso 1: buscar ofertas",
        "Estamos recorriendo las fuentes seleccionadas para reunir oportunidades relevantes.",
    )
    progress_scrape.progress(0)

    all_jobs = []
    seen_global = set()
    platforms_enabled = {
        "Remotive":       use_remotive,
        "Arbeitnow":      use_arbeitnow,
        "WeWorkRemotely": use_wwr,
        "Himalayas":      use_himalayas,
    }
    enabled_list = [p for p, v in platforms_enabled.items() if v]
    total_platforms = len(enabled_list)
    scrape_started_at = time.monotonic()

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(f"Buscando ofertas en **{platform_name}**...")
        if max_results_limit > 0 and len(all_jobs) >= max_results_limit:
            platform_status.success(f"✅ Se alcanzó el límite configurado de {max_results_limit} ofertas.")
            platform_eta.info("Tiempo restante estimado: 0 s")
            break
        try:
            if platform_name == "Remotive":
                jobs = sc.scrape_remotive(
                    keywords,
                    max_results=max_results_limit - len(all_jobs) if max_results_limit > 0 else 0,
                )
            elif platform_name == "Arbeitnow":
                jobs = sc.scrape_arbeitnow(
                    keywords,
                    max_results=max_results_limit - len(all_jobs) if max_results_limit > 0 else 0,
                )
            elif platform_name == "WeWorkRemotely":
                jobs = sc.scrape_weworkremotely(
                    max_results=max_results_limit - len(all_jobs) if max_results_limit > 0 else 0,
                )
            elif platform_name == "Himalayas":
                jobs = sc.scrape_himalayas(
                    keywords,
                    max_results=max_results_limit - len(all_jobs) if max_results_limit > 0 else 0,
                )
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

        completed_platforms = idx + 1
        progress_scrape.progress(completed_platforms / total_platforms)
        elapsed = time.monotonic() - scrape_started_at
        avg_per_platform = elapsed / completed_platforms
        remaining_platforms = total_platforms - completed_platforms
        eta_seconds = avg_per_platform * remaining_platforms
        platform_eta.info(f"Tiempo restante estimado: {format_duration(eta_seconds)}")

    platform_status.success(f"✅ Búsqueda terminada: se encontraron **{len(all_jobs)} ofertas únicas**.")
    platform_eta.info(f"Tiempo total: {format_duration(time.monotonic() - scrape_started_at)}")

    # ── STEP 2: AI Scoring ────────────────────────────────────────────────────
    ai_status, ai_notice, ai_eta, progress_ai, live_results = render_workflow_step(
        2,
        "Paso 2: analizar cada oferta con IA",
        "Ahora evaluamos qué tan bien encaja cada oferta con tu perfil.",
    )
    progress_ai.progress(0)

    scored_jobs  = []
    top_so_far   = []
    quota_exceeded = False
    scoring_started_at = time.monotonic()
    total_jobs = len(all_jobs)

    for i, job in enumerate(all_jobs):
        ai_status.info(f"Analizando oferta **{i+1} de {total_jobs}**: {job.title[:50]} @ {job.company}")
        data  = ai_engine.score_job(job)
        score = data.get("score", 0)
        if data.get("quota_exceeded", False):
            quota_exceeded = True
            ai_notice.error(f"⚠️ Se agotó la cuota diaria de Gemini. Se alcanzaron a evaluar {i} ofertas. Podés continuar mañana.")
            break

        from ai_engine import ScoredJob
        sj = ScoredJob(
            job=job,
            score=score,
            match_reasons=data.get("match_reasons", []),
            missing_skills=data.get("missing_skills", []),
            cover_letter=None,
            summary=data.get("summary", ""),
        )
        scored_jobs.append(sj)

        if score >= min_score:
            top_so_far.append(sj)

        # Mostrar top matches en tiempo real
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

        completed_jobs = i + 1
        progress_ai.progress(completed_jobs / total_jobs)
        elapsed = time.monotonic() - scoring_started_at
        avg_per_job = elapsed / completed_jobs
        remaining_jobs = total_jobs - completed_jobs
        eta_seconds = avg_per_job * remaining_jobs
        ai_eta.info(f"Tiempo restante estimado: {format_duration(eta_seconds)}")
        time.sleep(0.1)

    scored_jobs.sort(key=lambda x: x.score, reverse=True)
    top_matches = [j for j in scored_jobs if j.score >= min_score]
    if not quota_exceeded:
        ai_status.success(f"✅ Análisis terminado: **{len(top_matches)} ofertas** superan el puntaje mínimo de {min_score}.")
        ai_eta.info(f"Tiempo total: {format_duration(time.monotonic() - scoring_started_at)}")

    # ── STEP 3: Cover Letters ─────────────────────────────────────────────────
    if top_matches:
        cl_status, _, cl_eta, progress_cl, _ = render_workflow_step(
            3,
            "Paso 3: generar cartas personalizadas",
            "Estamos preparando una carta para cada oportunidad recomendada.",
        )
        progress_cl.progress(0)
        cover_started_at = time.monotonic()
        total_letters = len(top_matches)

        for i, sj in enumerate(top_matches):
            cl_status.info(f"Generando carta **{i+1} de {total_letters}** para {sj.job.title}")
            sj.cover_letter = ai_engine.generate_cover_letter(
                sj.job, {"match_reasons": sj.match_reasons}
            )
            completed_letters = i + 1
            progress_cl.progress(completed_letters / total_letters)
            elapsed = time.monotonic() - cover_started_at
            avg_per_letter = elapsed / completed_letters
            remaining_letters = total_letters - completed_letters
            eta_seconds = avg_per_letter * remaining_letters
            cl_eta.info(f"Tiempo restante estimado: {format_duration(eta_seconds)}")

        cl_status.success("✅ Cartas generadas.")
        cl_eta.info(f"Tiempo total: {format_duration(time.monotonic() - cover_started_at)}")

    # ── STEP 4: Email opcional ─────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        email_status, _, email_eta, _, _ = render_workflow_step(
            4,
            "Paso 4: enviar resumen por email",
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
            email_status.success(f"✅ Se envió el resumen a **{email_recipient}**.")
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
            "score": sj.score,
            "title": sj.job.title,
            "company": sj.job.company,
            "source": sj.job.source,
            "url": sj.job.url,
            "match_reasons": sj.match_reasons,
            "summary": sj.summary,
            "has_cover_letter": sj.cover_letter is not None,
        }
        for sj in scored_jobs
    ]
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)

    # ── RESULTADOS ─────────────────────────────────────────────────────────────
    with results_placeholder.container():
        st.markdown('<span id="results-anchor" class="results-anchor"></span>', unsafe_allow_html=True)
        components.html(
            """
            <script>
            const anchor = window.parent.document.getElementById("results-anchor");
            if (anchor) {
              anchor.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            </script>
            """,
            height=0,
        )
        st.header("📊 Resultados")
        st.caption("Revisá las mejores oportunidades y descargá las cartas o el resumen completo.")

        # Métricas resumen
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ofertas analizadas", len(scored_jobs))
        c2.metric("Ofertas recomendadas", len(top_matches))
        c3.metric(
            "Mejor puntaje",
            f"{scored_jobs[0].score}/100" if scored_jobs else "—",
            scored_jobs[0].job.title[:30] if scored_jobs else "",
        )
        dist_80 = sum(1 for j in scored_jobs if j.score >= 80)
        c4.metric("Muy buenas (80+)", dist_80)

        def render_job_card(sj, idx, section):
            score = sj.score
            color  = "score-high"   if score >= 80 else \
                     "score-medium" if score >= 60 else "score-low"
            src_class = {
                "Remotive":       "src-remotive",
                "Arbeitnow":      "src-arbeitnow",
                "WeWorkRemotely": "src-wwr",
                "Himalayas":      "src-himalayas",
            }.get(sj.job.source, "src-remotive")

            with st.expander(
                f"{score}/100 — {sj.job.title}  @  {sj.job.company}",
                expanded=(idx == 0),
            ):
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
                    st.markdown(
                        f'<div class="cover-letter-box">{sj.cover_letter}</div>',
                        unsafe_allow_html=True,
                    )
                    unique_key = f"dl_{section}_{sj.job.id}_{idx}"
                    st.download_button(
                        "⬇ Descargar carta",
                        data=sj.cover_letter,
                        file_name=f"cover_{sj.job.company.replace(' ','_')}_{sj.job.title[:20].replace(' ','_')}.txt",
                        mime="text/plain",
                        key=unique_key,
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
