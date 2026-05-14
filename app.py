"""
app.py — Job Hunter UI con Streamlit
Interfaz web para configurar y correr el job hunter sin tocar código
"""

import streamlit as st
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
    div[data-testid="stExpander"] { border: 1px solid #e2e8f0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar: Configuración ──────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Job Hunter AI")
    st.caption("Configurá tu búsqueda y buscá ofertas con IA")

    st.divider()

    # ── Credenciales ──────────────────────────────────────────────────────────
    st.header("🔑 Credenciales")

    with st.expander("¿Cómo conseguir la API Key de Gemini?", icon="❓"):
        st.markdown("""
1. Ir a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Iniciar sesión con Google
3. Click en **Create API Key**
4. Copiar la clave (empieza con `AIza...`)

Es **gratuita** — no necesitás tarjeta.
        """)

    gemini_key = st.text_input(
        "API Key de Gemini",
        type="password",
        placeholder="AIzaXXXXXXXXXXXXXXXXX",
        help="Tu clave de Google Gemini (gratuita)",
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
        "Modelo de IA",
        available_models,
        index=0,
        help="gemini-3.1-flash-lite tiene el mejor free tier (500 req/día)",
    )

    st.divider()

    # ── Email (OPCIONAL) ────────────────────────────────────────────────────────
    # Inicializar variables de email (por si no se tilda el checkbox)
    email_sender = ""
    email_password = ""
    email_recipient = ""
    
    send_email = st.checkbox("📧 Enviar digest por email al terminar", value=False)

    if send_email:
        with st.expander("¿Cómo conseguir el App Password de Gmail?", icon="❓"):
            st.markdown("""
1. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Verificación en 2 pasos debe estar **activada**
3. En "Nombre de la app" escribir `Job Hunter`
4. Click **Crear** → copiar los 16 caracteres
5. Usarlos abajo (sin espacios)

⚠️ **NO** uses tu contraseña normal de Gmail.
            """)

        email_sender = st.text_input(
            "Tu Gmail",
            placeholder="tu@gmail.com",
        )
        email_password = st.text_input(
            "App Password (16 caracteres)",
            type="password",
            placeholder="abcdefghijklmnop",
        )
        email_recipient = st.text_input(
            "Email destino del digest",
            placeholder="tu@gmail.com",
            help="Puede ser el mismo Gmail u otro email",
        )
    
    st.divider()

    # ── Búsqueda ───────────────────────────────────────────────────────────────
    st.header("🔍 Búsqueda")

    keywords_raw = st.text_area(
        "Keywords (una por línea)",
        value="backend developer\njava spring boot\ncloud engineer\nbackend engineer\ndevops engineer",
        height=120,
        help="Palabras clave para buscar en las plataformas",
    )

    min_score = st.slider(
        "Score mínimo para incluir en digest",
        min_value=30,
        max_value=90,
        value=65,
        step=5,
        help="Ofertas con score menor a este valor no aparecen en el email",
    )

    st.subheader("Plataformas")
    col1, col2 = st.columns(2)
    with col1:
        use_remotive   = st.checkbox("Remotive",       value=True)
        use_arbeitnow  = st.checkbox("Arbeitnow",      value=True)
    with col2:
        use_wwr        = st.checkbox("WeWorkRemotely", value=True)
        use_himalayas  = st.checkbox("Himalayas",      value=True)

    st.divider()

    # ── Perfil del candidato ───────────────────────────────────────────────────
    st.header("👤 Tu perfil")
    candidate_profile = st.text_area(
        "Describí tu perfil (para que la IA evalúe el match)",
        value="""Rol buscado: Backend Engineer / Cloud Engineer (solo remoto)

Stack técnico:
- Java, Spring Boot, REST APIs, JWT, SQL (PostgreSQL, MySQL)
- Python, Bash scripting, automatización
- Docker, Cloud Deployment, Linux
- ERP: Odoo (implementación técnica end-to-end)
- Herramientas: Git, Jira, Scrum

Experiencia:
- IT Lead / Backend Engineer en SieteIdeas
- Java Backend Developer en SISP Tandil

Idiomas: Español (nativo), Inglés (intermedio)
Ubicación: Argentina — disponible 100% remoto""",
        height=200,
    )


# ─── Main area ───────────────────────────────────────────────────────────────
st.title("🎯 Job Hunter AI")
st.caption("Encontrá ofertas remotas que matcheen con tu perfil, con IA")

# Validación antes de correr
def validate_config():
    errors = []
    if not gemini_key or not gemini_key.startswith("AIza"):
        errors.append("❌ API Key de Gemini inválida o vacía")
    
    if send_email:
        if not email_sender or "@" not in email_sender:
            errors.append("❌ Si envías email: Gmail sender requerido")
        if not email_password or len(email_password.replace(" ","")) != 16:
            errors.append("❌ Si envías email: App Password debe tener exactamente 16 caracteres (sin espacios)")
        if not email_recipient or "@" not in email_recipient:
            errors.append("❌ Si envías email: email recipient requerido")
    
    keywords = [k.strip() for k in keywords_raw.strip().splitlines() if k.strip()]
    if not keywords:
        errors.append("❌ Agregá al menos una keyword")
    
    platforms = any([use_remotive, use_arbeitnow, use_wwr, use_himalayas])
    if not platforms:
        errors.append("❌ Seleccioná al menos una plataforma")
    
    return errors

# ─── Run button ───────────────────────────────────────────────────────────────
col_btn, col_info = st.columns([2, 3])
with col_btn:
    run_button = st.button("🚀 Buscar ofertas ahora", type="primary", use_container_width=True)
with col_info:
    st.info("⏱ Tarda ~6-8 min · 90 ofertas · IA evalúa cada una")

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

    # ── STEP 1: Scraping ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Step 1 — Scraping de plataformas")

    platform_status = st.empty()
    progress_scrape = st.progress(0)

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

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(f"Scraping **{platform_name}**...")
        try:
            if platform_name == "Remotive":
                jobs = sc.scrape_remotive(keywords)
            elif platform_name == "Arbeitnow":
                jobs = sc.scrape_arbeitnow(keywords)
            elif platform_name == "WeWorkRemotely":
                jobs = sc.scrape_weworkremotely()
            elif platform_name == "Himalayas":
                jobs = sc.scrape_himalayas(keywords)
            else:
                jobs = []

            for job in jobs:
                key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
                if key not in seen_global:
                    seen_global.add(key)
                    all_jobs.append(job)

        except Exception as e:
            st.warning(f"⚠️ Error en {platform_name}: {e}")

        progress_scrape.progress((idx + 1) / total_platforms)

    platform_status.success(f"✅ Scraping completado — **{len(all_jobs)} ofertas únicas** encontradas")

    # ── STEP 2: AI Scoring ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Step 2 — Evaluación con IA")

    ai_status    = st.empty()
    progress_ai  = st.progress(0)
    live_results = st.empty()

    scored_jobs  = []
    top_so_far   = []

    for i, job in enumerate(all_jobs):
        ai_status.info(f"Evaluando **{i+1}/{len(all_jobs)}** — {job.title[:50]} @ {job.company}")
        data  = ai_engine.score_job(job)
        score = data.get("score", 0)

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
            st.caption("🔥 Top matches hasta ahora:")
            for t in top5:
                color = "score-high" if t.score >= 80 else "score-medium" if t.score >= 60 else "score-low"
                st.markdown(
                    f'<span class="score-badge {color}">{t.score}/100</span> '
                    f'**{t.job.title}** @ {t.job.company}',
                    unsafe_allow_html=True,
                )

        progress_ai.progress((i + 1) / len(all_jobs))
        time.sleep(0.1)

    scored_jobs.sort(key=lambda x: x.score, reverse=True)
    top_matches = [j for j in scored_jobs if j.score >= min_score]
    ai_status.success(f"✅ Evaluación completada — **{len(top_matches)} matches** sobre umbral de {min_score}")

    # ── STEP 3: Cover Letters ─────────────────────────────────────────────────
    if top_matches:
        st.divider()
        st.subheader("Step 3 — Generando cover letters")
        cl_status   = st.empty()
        progress_cl = st.progress(0)

        for i, sj in enumerate(top_matches):
            cl_status.info(f"Cover letter **{i+1}/{len(top_matches)}** — {sj.job.title}")
            sj.cover_letter = ai_engine.generate_cover_letter(
                sj.job, {"match_reasons": sj.match_reasons}
            )
            progress_cl.progress((i + 1) / len(top_matches))

        cl_status.success("✅ Cover letters generadas")

    # ── STEP 4: Email opcional ─────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        st.divider()
        st.subheader("Step 4 — Enviando digest por email")
        try:
            from notifier import send_digest
            cfg.EMAIL_SENDER    = email_sender
            cfg.EMAIL_PASSWORD  = email_password
            cfg.EMAIL_RECIPIENT = email_recipient
            send_digest(scored_jobs)
            st.success(f"✅ Digest enviado a **{email_recipient}**")
        except Exception as e:
            st.error(f"❌ Error enviando email: {e}")

    # ── RESULTADOS ─────────────────────────────────────────────────────────────
    st.divider()
    st.header("📊 Resultados")

    # Métricas resumen
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ofertas analizadas", len(scored_jobs))
    c2.metric("Matches encontrados", len(top_matches))
    c3.metric(
        "Top score",
        f"{scored_jobs[0].score}/100" if scored_jobs else "—",
        scored_jobs[0].job.title[:30] if scored_jobs else "",
    )
    dist_80 = sum(1 for j in scored_jobs if j.score >= 80)
    c4.metric("Excelentes (80+)", dist_80)

    st.divider()

    # ── Tabs: Top matches / Todas las ofertas
    tab1, tab2 = st.tabs([
        f"🔥 Top matches ({len(top_matches)})",
        f"📋 Todas las ofertas ({len(scored_jobs)})",
    ])

    def render_job_card(sj, idx):
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
                    st.link_button("Ver oferta →", sj.job.url, use_container_width=True)

            r1, r2 = st.columns(2)
            with r1:
                st.markdown("**✅ Por qué matchea**")
                for reason in sj.match_reasons:
                    st.markdown(f"- {reason}")
            with r2:
                st.markdown("**⚠️ Skills faltantes**")
                if sj.missing_skills:
                    for skill in sj.missing_skills:
                        st.markdown(f"- {skill}")
                else:
                    st.markdown("- Ninguno crítico")

            if sj.cover_letter:
                st.markdown("**📝 Cover letter generada**")
                st.markdown(
                    f'<div class="cover-letter-box">{sj.cover_letter}</div>',
                    unsafe_allow_html=True,
                )
                st.download_button(
                    "⬇ Descargar cover letter",
                    data=sj.cover_letter,
                    file_name=f"cover_{sj.job.company.replace(' ','_')}_{sj.job.title[:20].replace(' ','_')}.txt",
                    mime="text/plain",
                    key=f"dl_{idx}",
                )

    with tab1:
        if top_matches:
            for i, sj in enumerate(top_matches):
                render_job_card(sj, i)
        else:
            st.info(f"No se encontraron matches sobre {min_score} puntos. Probá bajando el score mínimo en la barra lateral.")

    with tab2:
        st.caption("Todas las ofertas ordenadas por score")
        for i, sj in enumerate(scored_jobs):
            render_job_card(sj, i)

    # Guardar resultados en JSON
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

    st.download_button(
        "⬇ Descargar resultados completos (JSON)",
        data=json.dumps(data_out, ensure_ascii=False, indent=2),
        file_name=f"job_hunt_{ts}.json",
        mime="application/json",
    )

else:
    # Estado inicial — instrucciones
    st.markdown("""
### 👈 Configurá todo en la barra lateral y hacé click en **Buscar ofertas ahora**

**¿Qué hace esta app?**
1. 🔍 Scrapea ofertas remotas en Remotive, Arbeitnow, WeWorkRemotely e Himalayas
2. 🤖 Evalúa cada oferta con IA según tu perfil (score 0-100)
3. ✍️ Genera cover letters personalizadas para los mejores matches
4. 📧 Opcionalmente te manda un digest al email

**Requisitos:**
- API Key de Gemini (gratis en [aistudio.google.com](https://aistudio.google.com/app/apikey))
- Gmail App Password (si querés el digest por email)
    """)

    st.info("💡 **Tip:** Podés correrla sin email y ver los resultados directamente en pantalla.")
