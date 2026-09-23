"""
app.py — Job Hunter UI con Streamlit
"""

import streamlit as st
import streamlit.components.v1 as components
import hashlib
import json
import time
import os
from datetime import datetime
from pathlib import Path

import ai_engine
import candidate as cand
import matching
import normalize
import theme
import ui
from candidate import SENIORITY_LEVELS, CandidateProfile

# ─── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JobHunter",
    page_icon=str(Path(__file__).parent / "docs" / "brand" / "logo" / "favicon-32.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(theme.css(), unsafe_allow_html=True)  # docs/brand/BRAND.md

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
    "selected_model":     ai_engine.DEFAULT_MODEL,
    "send_email":         False,
    "email_sender":       "",
    "email_password_raw": "",
    "email_recipient":    "",
    "keywords_list":      [],
    "kw_options":         [],
    "min_score":          65,
    # Preferencias (filtros duros). Vacío = cualquiera.
    "pref_modalities":    [],
    "pref_locations":     "",
    "pref_languages":     [],
    "eval_limit":         matching.DEFAULT_TOP_N,   # ofertas que evalúa el LLM
    "use_remotive":       True,
    "use_arbeitnow":      True,
    "use_wwr":            True,
    "use_himalayas":      True,
    "use_remoteok":       True,
    "use_jobicy":         True,
    "use_getonboard":     True,
    "use_puentetalent":   True,
    "use_latojobs":       True,
    "use_workingnomads":  True,
    "use_themuse":        True,
    "use_remoteco":       True,
    "use_jobspresso":     True,
    "use_justjoinit":     False,
    "use_authenticjobs":  True,
    "result_page":        0,
    "result_page_all":    0,
    "profile":            None,   # CandidateProfile.to_dict()
    "funnel":             None,   # resumen de la última búsqueda (transparencia)
    "scored_jobs":        [],   # persiste entre reruns de paginación
    "top_matches":        [],   # idem
    "min_score_last":     65,   # score usado en la última búsqueda (para métricas)
    # ── Preferencias visuales ─────────────────────────────────────────────
    "dark_mode":          False,  # False = light (default), True = dark
    "lang":               "es",   # "es" = Español (default), "en" = English
    # ── Control de búsqueda en curso ──────────────────────────────────
    "is_searching":       False,  # True mientras la búsqueda corre
    "cancel_search":      False,  # señal para abortar entre plataformas
    "cancel_and_config":  False,  # abortar Y abrir wizard
    # Estado interno del scraping por pasos (permite cancelar entre plataformas)
    "_scrape_phase":      "idle",   # idle | scraping | scoring | letters | done
    "_scrape_idx":        0,        # índice de plataforma actual
    "_scrape_jobs":       [],       # acumulador de trabajos scrapeados
    "_scrape_seen":       set(),    # deduplicación entre plataformas
    "_scrape_cfg":        {},       # config snapshot al iniciar búsqueda
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Preferencias visuales: query params → session_state (solo al iniciar) ───
# La URL (?lang=en&theme=dark) conserva las preferencias al recargar o compartir.
if "_prefs_loaded" not in st.session_state:
    st.session_state._prefs_loaded = True
    _qp = st.query_params
    _lv = _qp.get("lang")
    if _lv not in ("es", "en"):
        # Sin preferencia explícita: idioma del navegador (inglés o español).
        _locale = (getattr(st.context, "locale", None) or "es").lower()
        _lv = "en" if _locale.startswith("en") else "es"
    st.session_state.lang = _lv
    st.session_state.dark_mode = (_qp.get("theme") == "dark")

# ─── Modo demo (solo desarrollo, JOB_HUNTER_DEMO=1): UI con datos ficticios, sin IA ──
import demo as _demo
if _demo.enabled() and "_demo_loaded" not in st.session_state:
    st.session_state._demo_loaded = True
    _dp, _ds = _demo.load()
    st.session_state.profile        = _dp.to_dict()
    st.session_state.cv_analyzed    = True
    st.session_state.keywords_list  = _dp.all_search_terms()
    st.session_state["kw_options"]  = list(st.session_state.keywords_list)
    st.session_state.scored_jobs    = _ds
    st.session_state.top_matches    = [s for s in _ds if s.score >= st.session_state.min_score]
    st.session_state.min_score_last = st.session_state.min_score
    st.session_state.search_done    = True
    st.session_state.funnel = {"found": 112, "dups": 6, "excluded": {"modality": 9, "language": 4, "location": 3},
                               "out": 50, "evaluated": len(_ds), "top_n": 40, "emb_failed": False}

# ─── Traducciones: i18n.py ─────────────────────────────────────────────────────
from i18n import TRANSLATIONS



def _t(key: str, **kw) -> str:
    """Devuelve el texto en el idioma activo, interpolando kwargs si los hay."""
    lang = st.session_state.get("lang", "es")
    d    = TRANSLATIONS.get(lang, TRANSLATIONS["es"])
    txt  = d.get(key, TRANSLATIONS["es"].get(key, key))
    return txt.format(**kw) if kw else txt


# ─── Toolbar: tema e idioma ───────────────────────────────────────────────────
# Todo del lado del servidor: cambiar idioma o tema hace un rerun, no recarga
# la página, así que la sesión (API key, CV analizado, resultados) se conserva.
def _on_lang_change():
    st.session_state.lang = st.session_state._lang_widget
    st.query_params["lang"] = st.session_state.lang


def _on_theme_change():
    st.session_state.dark_mode = (st.session_state._theme_widget == "dark")
    st.query_params["theme"] = st.session_state._theme_widget


st.session_state._lang_widget  = st.session_state.lang
st.session_state._theme_widget = "dark" if st.session_state.dark_mode else "light"

def _render_nav() -> None:
    """Logo (versión según el fondo, BRAND.md §3) + idioma y tema."""
    logo = theme.logo_svg("lockup-dark" if st.session_state.dark_mode else "lockup-light")
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.markdown(ui.nav_html(logo, _t), unsafe_allow_html=True)
    with right:
        with st.container(horizontal=True, horizontal_alignment="right", key="jh_toolbar"):
            st.segmented_control(
                _t("theme_label"), ["light", "dark"], required=True,
                format_func={"light": "☀️", "dark": "🌙"}.get,
                key="_theme_widget", on_change=_on_theme_change, label_visibility="collapsed",
            )
            st.segmented_control(
                _t("lang_label"), ["es", "en"], required=True,
                format_func=str.upper,
                key="_lang_widget", on_change=_on_lang_change, label_visibility="collapsed",
            )


_render_nav()
st.markdown(theme.uploader_css(_t("up_button"), _t("up_hint", mb=10)), unsafe_allow_html=True)

# El CSS del modo oscuro cuelga de html[data-theme]. El iframe se vuelve a
# ejecutar solo cuando cambia su contenido, o sea, cuando cambia el tema.
_theme = "dark" if st.session_state.dark_mode else "light"
components.html(
    f"<script>window.parent.document.documentElement.setAttribute('data-theme','{_theme}');</script>",
    height=0,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def validate_config():
    errors = []
    if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
        errors.append(_t("val_key"))
    if st.session_state.send_email:
        if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
            errors.append(_t("val_email"))
        if len(st.session_state.email_password_raw.replace(" ", "")) != 16:
            errors.append(_t("val_pass"))
        if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
            errors.append(_t("val_recip"))
    if not st.session_state.keywords_list:
        errors.append(_t("val_no_kw"))
    if (_get_profile() or CandidateProfile()).is_empty():
        errors.append(_t("val_no_profile"))
    if not any([st.session_state.use_remotive, st.session_state.use_arbeitnow,
                st.session_state.use_wwr, st.session_state.use_himalayas,
                st.session_state.use_remoteok, st.session_state.use_jobicy,
                st.session_state.use_getonboard, st.session_state.use_puentetalent,
                st.session_state.use_latojobs, st.session_state.use_workingnomads,
                st.session_state.use_themuse, st.session_state.use_remoteco,
                st.session_state.use_jobspresso, st.session_state.use_justjoinit,
                st.session_state.use_authenticjobs]):
        errors.append(_t("val_no_src"))
    return errors


def format_duration(seconds):
    seconds = max(0, int(round(seconds)))
    m, s = divmod(seconds, 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


# ─── Perfil del candidato (estructurado) ──────────────────────────────────────
JOB_LANG_CODES = ["es", "en", "pt", "de", "fr"]
_LANG_NAME_HINTS = {
    "es": ("espa", "castellano", "spanish"),
    "en": ("ingl", "english"),
    "pt": ("portug",),
    "de": ("alem", "german", "deutsch"),
    "fr": ("franc", "french"),
}


def _get_profile() -> CandidateProfile | None:
    d = st.session_state.get("profile")
    return CandidateProfile.from_dict(d) if d else None


def _set_profile(p: CandidateProfile) -> None:
    st.session_state.profile = p.to_dict()


def _job_lang_codes(p: CandidateProfile) -> list[str]:
    """Idiomas de oferta aceptables según el CV (sugerencia que el usuario puede cambiar)."""
    names = [normalize.strip_accents(l.language.lower()) for l in p.languages]
    return [code for code, hints in _LANG_NAME_HINTS.items()
            if p.cv_language == code or any(h in n for n in names for h in hints)]


def _store_cv(uploaded) -> None:
    """Guarda el CV subido en la sesión (en memoria, nunca en disco)."""
    data = uploaded.getvalue()
    blob_id = hashlib.sha256(data).hexdigest()[:16]
    if (st.session_state.get("cv_blob") or {}).get("id") != blob_id:
        st.session_state.cv_blob = {"name": uploaded.name, "type": uploaded.type, "data": data, "id": blob_id}
        st.session_state.manual_profile = False


def _analyze_cv(blob: dict) -> CandidateProfile | None:
    try:
        contents = cand.cv_contents(blob["data"], blob["type"])
        return cand.extract_profile(contents, api_key=st.session_state.gemini_key,
                                    model=st.session_state.selected_model)
    except Exception as e:
        st.error(_t("cv_error", error=e))
        return None


def _lang_label(l) -> str:
    return f"{l.language} ({l.level})" if l.level and l.level != cand.UNKNOWN else l.language


def _parse_lang_label(label: str) -> cand.Language:
    import re as _re
    m = _re.match(r"^(.*?)\s*\((.*)\)\s*$", label)
    return cand.Language(language=m.group(1).strip(), level=m.group(2).strip()) if m else cand.Language(label.strip())


def _uniq(items) -> list[str]:
    """Sin duplicados (multiselect falla con opciones repetidas), respetando el orden."""
    return list(dict.fromkeys(i for i in items if i))


def _render_profile_editor(p: CandidateProfile) -> CandidateProfile:
    """Perfil extraído del CV, editable. Lo que la IA no encontró queda como 'no especificado'."""
    st.markdown(_t("prof_title"))
    st.caption(_t("prof_caption"))
    p.summary = st.text_area(_t("prof_summary"), value=p.summary, height=90)
    c1, c2 = st.columns(2)
    with c1:
        p.target_roles = st.multiselect(_t("prof_roles"), options=_uniq(p.target_roles), default=_uniq(p.target_roles),
                                        accept_new_options=True, help=_t("prof_roles_help"))
        p.seniority = st.selectbox(_t("prof_seniority"), SENIORITY_LEVELS,
                                   index=SENIORITY_LEVELS.index(p.seniority),
                                   format_func=lambda s: _t(f"sen_{s}"))
        p.years_experience = st.number_input(_t("prof_years"), value=p.years_experience, min_value=0.0,
                                             max_value=60.0, step=0.5, help=_t("prof_years_help"))
    with c2:
        loc = st.text_input(_t("prof_location"), value="" if p.location == cand.UNKNOWN else p.location,
                            placeholder=_t("prof_unknown"))
        p.location = loc.strip() or cand.UNKNOWN
        lang_labels = _uniq(_lang_label(l) for l in p.languages)
        chosen = st.multiselect(_t("prof_languages"), options=lang_labels, default=lang_labels,
                                accept_new_options=True, help=_t("prof_languages_help"))
        p.languages = [_parse_lang_label(x) for x in chosen]
    skill_names = _uniq(s.name for s in p.skills)
    kept = st.multiselect(_t("prof_skills"), options=skill_names, default=skill_names, accept_new_options=True)
    by_name = {s.name: s for s in p.skills}
    p.skills = [by_name.get(n) or cand.Skill(name=n, evidence=_t("prof_added_by_user")) for n in kept]

    with st.expander(_t("prof_evidence")):
        none = _t("prof_unknown")
        st.caption(f"{_t('prof_seniority')}: {p.seniority_evidence or none}")
        st.caption(f"{_t('prof_years')}: {p.years_evidence or none}")
        for s in p.skills:
            st.caption(f"{s.name}: {s.evidence or none}")
    return p


# ─── Wizard inline (sin @st.dialog para garantizar cierre correcto) ───────────
def show_config_wizard():
    step = st.session_state.config_step

    h_col, close_col = st.columns([5, 1], vertical_alignment="center")
    with h_col:
        st.markdown(f'<h2 class="jh-title">{_t("wiz_title")}</h2><p class="jh-meta">{_t("wiz_copy")}</p>',
                    unsafe_allow_html=True)
    with close_col:
        if st.button(_t("wiz_close"), type="tertiary", use_container_width=True, key="wizard_cancel",
                     help=_t("wiz_close_help")):
            st.session_state.show_dialog = False
            st.rerun()

    st.markdown(ui.stepper_html(step, [_t("wz1"), _t("wz2"), _t("wz3"), _t("wz4")]), unsafe_allow_html=True)

    # ── Paso 1: CV ────────────────────────────────────────────────────────
    if step == 1:
        with st.container(border=True):
            st.markdown(_t("step2_header"))
            st.caption(_t("step2_caption"))
            _up = st.file_uploader(_t("step2_file"), type=["pdf", "docx", "txt"],
                                   label_visibility="collapsed", key="cv_upload_wizard")
            if _up is not None:
                _store_cv(_up)
            _blob = st.session_state.get("cv_blob")
            if _blob:
                st.success(_t("step_cv_loaded", name=_blob["name"]), icon="📄")
            elif st.session_state.get("manual_profile"):
                st.info(_t("step_cv_manual"), icon="✍️")

        c_alt, c_next = st.columns(2)
        with c_alt:
            if st.button(_t("step_cv_or"), type="tertiary", use_container_width=True):
                st.session_state.manual_profile = True
                st.session_state.cv_blob = None
                st.session_state.config_step = 2
                st.rerun()
        with c_next:
            _ready = bool(st.session_state.get("cv_blob") or st.session_state.get("manual_profile"))
            if st.button(_t("btn_continue"), type="primary", use_container_width=True, disabled=not _ready):
                st.session_state.config_step = 2
                st.rerun()

    # ── Paso 2: Acceso a la IA ────────────────────────────────────────────
    elif step == 2:
        with st.container(border=True):
            st.markdown(_t("step1_header"))
            with st.expander(_t("step1_gemini_help"), icon="❓"):
                st.markdown(_t("help_gemini_steps"))
            st.session_state.gemini_key = st.text_input(
                _t("step1_key_label"),
                value=st.session_state.gemini_key,
                type="password",
                placeholder="AIzaXXXXXXXXXXXXXXXXX",
            )
            _models = ai_engine.AVAILABLE_MODELS
            if st.session_state.selected_model not in _models:
                st.session_state.selected_model = ai_engine.DEFAULT_MODEL
            _idx = _models.index(st.session_state.selected_model)
            st.session_state.selected_model = st.selectbox(_t("step1_model_label"), _models, index=_idx)

        with st.container(border=True):
            st.checkbox(_t("step1_email_chk"), key="send_email")
            if st.session_state.send_email:
                with st.expander(_t("step1_email_help"), icon="❓"):
                    st.markdown(_t("help_gmail_steps"))
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.email_sender = st.text_input(
                        _t("step1_gmail_label"),
                        value=st.session_state.email_sender,
                        placeholder=_t("ph_email_sender"),
                    )
                with c2:
                    st.session_state.email_recipient = st.text_input(
                        _t("step1_recip_label"),
                        value=st.session_state.email_recipient,
                        placeholder=_t("ph_email_recip"),
                    )
                st.session_state.email_password_raw = st.text_input(
                    _t("step1_pass_label"),
                    value=st.session_state.email_password_raw,
                    type="password",
                    placeholder="abcd efgh ijkl mnop",
                )

        _blob = st.session_state.get("cv_blob")
        _needs_analysis = bool(_blob) and st.session_state.get("cv_analyzed_id") != _blob["id"]
        c_back, c_next = st.columns(2)
        with c_back:
            if st.button(_t("btn_back"), use_container_width=True):
                st.session_state.config_step = 1
                st.rerun()
        with c_next:
            if st.button(_t("btn_analyze_continue") if _needs_analysis else _t("btn_continue"),
                         type="primary", use_container_width=True):
                err = []
                if not st.session_state.gemini_key or not st.session_state.gemini_key.startswith("AIza"):
                    err.append(_t("err_key"))
                if st.session_state.send_email:
                    if not st.session_state.email_sender or "@" not in st.session_state.email_sender:
                        err.append(_t("err_email"))
                    if len(st.session_state.email_password_raw.replace(" ", "")) != 16:
                        err.append(_t("err_pass"))
                    if not st.session_state.email_recipient or "@" not in st.session_state.email_recipient:
                        err.append(_t("err_recip"))
                if err:
                    st.toast(" · ".join(err), icon="⚠️")
                elif _needs_analysis:
                    with st.spinner(_t("step2_spinning")):
                        extracted = _analyze_cv(_blob)
                    if extracted:
                        _set_profile(extracted)
                        kws = extracted.all_search_terms()
                        if kws:
                            st.session_state.keywords_list = kws
                            st.session_state["kw_options"] = list(kws)
                            st.session_state["kw_tags"] = list(kws)
                        st.session_state.pref_languages = _job_lang_codes(extracted)
                        st.session_state.cv_analyzed = True
                        st.session_state.cv_analyzed_id = _blob["id"]
                        st.toast(_t("toast_cv_ok", n=len(kws)), icon="✅")
                        st.session_state.config_step = 3
                        st.rerun()
                    else:
                        st.toast(_t("toast_cv_err"), icon="⚠️")
                else:
                    st.session_state.config_step = 3
                    st.rerun()

    # ── Paso 3: Perfil ────────────────────────────────────────────────────
    elif step == 3:
        _p = _get_profile() or CandidateProfile()
        _structured = bool(_p.summary or _p.target_roles or _p.skills or _p.experiences)
        with st.container(border=True):
            if _structured:
                _p = _render_profile_editor(_p)
                _p.notes = st.text_area(_t("prof_notes"), value=_p.notes, height=100)
            else:
                st.markdown(_t("step4_header"))
                st.caption(_t("step4_caption"))
                _p.notes = st.text_area("perfil", value=_p.notes, height=195,
                                        label_visibility="collapsed", placeholder=_t("step4_ph"))
            _set_profile(_p)
        if _p.is_empty():
            st.warning(_t("step4_warning"), icon="⚠️")

        c_back, c_next = st.columns(2)
        with c_back:
            if st.button(_t("btn_back"), use_container_width=True):
                st.session_state.config_step = 2
                st.rerun()
        with c_next:
            if st.button(_t("btn_continue"), type="primary", use_container_width=True, disabled=_p.is_empty()):
                st.session_state.config_step = 4
                st.rerun()

    # ── Paso 4: Búsqueda ──────────────────────────────────────────────────
    elif step == 4:
        with st.container(border=True):
            st.markdown(_t("step3_header"))

            # Procesar keyword pendiente ANTES de instanciar el multiselect
            if "_pending_add" in st.session_state:
                _kw = st.session_state.pop("_pending_add")
                if _kw:
                    if _kw not in st.session_state["kw_options"]:
                        st.session_state["kw_options"].append(_kw)
                    if _kw not in st.session_state.keywords_list:
                        st.session_state.keywords_list.append(_kw)
                st.session_state["kw_tags"] = list(st.session_state.keywords_list)

            if "kw_tags" not in st.session_state:
                st.session_state["kw_tags"] = list(st.session_state.keywords_list)

            selected = st.multiselect(
                _t("step3_kw_ph"),
                options=st.session_state["kw_options"],
                key="kw_tags",
                placeholder=_t("step3_kw_ph"),
                label_visibility="collapsed",
            )
            st.session_state.keywords_list = list(selected)

            with st.form("add_kw", clear_on_submit=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    new_kw = st.text_input(
                        "kw", placeholder=_t("step3_add_ph"),
                        label_visibility="collapsed",
                    )
                with c2:
                    add_submitted = st.form_submit_button(_t("step3_add_btn"), use_container_width=True)
                if add_submitted and new_kw.strip():
                    st.session_state["_pending_add"] = new_kw.strip()
                    st.rerun()

        with st.container(border=True):
            st.markdown(_t("step3_params"))
            st.caption(_t("pref_caption"))
            st.session_state.pref_modalities = st.multiselect(
                _t("pref_modality"), list(matching.MODALITIES),
                default=st.session_state.pref_modalities,
                format_func=lambda m: _t(f"mod_{m}"),
                placeholder=_t("pref_any"), help=_t("pref_modality_help"),
            )
            st.session_state.pref_locations = st.text_input(
                _t("pref_locations"), value=st.session_state.pref_locations,
                placeholder=_t("pref_locations_ph"), help=_t("pref_locations_help"),
            )
            st.session_state.pref_languages = st.multiselect(
                _t("pref_languages"), JOB_LANG_CODES,
                default=[c for c in st.session_state.pref_languages if c in JOB_LANG_CODES],
                format_func=lambda c: _t(f"lang_{c}"),
                placeholder=_t("pref_any"), help=_t("pref_languages_help"),
            )
            st.session_state.min_score = st.slider(
                _t("step3_score_label"),
                min_value=30, max_value=90, step=5,
                value=st.session_state.min_score,
                help=_t("step3_score_help"),
            )
            st.markdown(_t("step3_sources"))
            st.caption(_t("step3_global"))
            g1, g2, g3, g4, g5 = st.columns(5)
            with g1:
                st.session_state.use_remotive     = st.checkbox("Remotive",       value=st.session_state.use_remotive)
            with g2:
                st.session_state.use_himalayas    = st.checkbox("Himalayas",      value=st.session_state.use_himalayas)
            with g3:
                st.session_state.use_remoteok     = st.checkbox("RemoteOK",       value=st.session_state.use_remoteok)
            with g4:
                st.session_state.use_jobicy       = st.checkbox("Jobicy",         value=st.session_state.use_jobicy)
            with g5:
                st.session_state.use_workingnomads = st.checkbox("WorkingNomads", value=st.session_state.use_workingnomads)

            st.caption(_t("step3_latam"))
            l1, l2, l3, l4, l5 = st.columns(5)
            with l1:
                st.session_state.use_getonboard   = st.checkbox("Get on Board",   value=st.session_state.use_getonboard)
            with l2:
                st.session_state.use_latojobs     = st.checkbox("LatoJobs",       value=st.session_state.use_latojobs)
            with l3:
                st.session_state.use_puentetalent = st.checkbox("Puente Talent",  value=st.session_state.use_puentetalent)
            with l4:
                st.empty()
            with l5:
                st.empty()

            st.caption(_t("step3_us"))
            a1, a2, a3, a4, a5 = st.columns(5)
            with a1:
                st.session_state.use_arbeitnow    = st.checkbox("Arbeitnow",      value=st.session_state.use_arbeitnow)
            with a2:
                st.session_state.use_wwr          = st.checkbox("WeWorkRemotely", value=st.session_state.use_wwr)
            with a3:
                st.session_state.use_themuse      = st.checkbox("The Muse",       value=st.session_state.use_themuse)
            with a4:
                st.session_state.use_jobspresso   = st.checkbox("Jobspresso",     value=st.session_state.use_jobspresso)
            with a5:
                st.session_state.use_remoteco     = st.checkbox("Remote.co",      value=st.session_state.use_remoteco)

            st.caption(_t("step3_eu"))
            e1, _ = st.columns([1, 4])
            with e1:
                st.session_state.use_justjoinit   = st.checkbox("JustJoin.it",   value=st.session_state.use_justjoinit)

            st.caption(_t("step3_other"))
            o1, _ = st.columns([1, 4])
            with o1:
                st.session_state.use_authenticjobs = st.checkbox("AuthenticJobs", value=st.session_state.use_authenticjobs)

            st.session_state.eval_limit = st.slider(
                _t("eval_limit_label"), min_value=10, max_value=200, step=10,
                value=st.session_state.eval_limit, help=_t("eval_limit_help"),
            )

        c_back, c_start = st.columns(2)
        with c_back:
            if st.button(_t("btn_back"), use_container_width=True):
                st.session_state.config_step = 3
                st.rerun()
        with c_start:
            if st.button(_t("btn_start"), type="primary", use_container_width=True):
                errors = validate_config()
                if errors:
                    st.toast(" · ".join(errors), icon="⚠️")
                else:
                    st.session_state.show_dialog   = False
                    st.session_state.run_search    = True
                    st.session_state.is_searching  = True   # ← debe estar True ANTES del rerun
                    st.session_state.search_done   = False
                    st.session_state.cancel_search = False
                    st.session_state.scored_jobs   = []
                    st.session_state.top_matches   = []
                    st.rerun()  # rerun desde contexto principal — siempre full-page


# ─── Wizard (toma la pantalla completa cuando está activo) ────────────────────
# Si el usuario vino de "Detener & Configurar", abrir en paso 3 (keywords/fuentes)
# para que pueda ajustar rápidamente y relanzar.
if st.session_state.cancel_and_config:
    st.session_state.cancel_and_config = False
    st.session_state.show_dialog       = True
    st.session_state.config_step       = 3   # Abre en Keywords/Fuentes directamente

if st.session_state.show_dialog:
    show_config_wizard()
    st.stop()

# ─── Landing ──────────────────────────────────────────────────────────────────
N_PORTALS = sum(1 for k in _defaults if k.startswith("use_"))


def _open_wizard(step: int) -> None:
    st.session_state.show_dialog = True
    st.session_state.config_step = step
    st.rerun()


_searching = st.session_state.run_search or st.session_state.is_searching
_landing = not _searching and not st.session_state.search_done

if _landing:
    hero_l, hero_r = st.columns([1.05, 0.95], gap="large", vertical_alignment="center")
    with hero_l:
        st.markdown(ui.hero_copy_html(_t, N_PORTALS), unsafe_allow_html=True)
        _hero_cv = st.file_uploader(_t("hero_upload_label"), type=["pdf", "docx", "txt"],
                                    key="cv_upload_hero", label_visibility="collapsed")
        if _hero_cv is not None and (st.session_state.get("cv_blob") or {}).get("name") != _hero_cv.name:
            _store_cv(_hero_cv)
            _open_wizard(2)   # con el CV cargado, el siguiente paso es el acceso a la IA
        if st.button(_t("hero_write"), type="tertiary"):
            st.session_state.manual_profile = True
            st.session_state.cv_blob = None
            _open_wizard(2)
        st.markdown(ui.proof_html(_t), unsafe_allow_html=True)
    with hero_r:
        st.markdown(ui.mosaic_html(_t), unsafe_allow_html=True)
    st.markdown(ui.band_html(_t, N_PORTALS) + ui.steps_html(_t) + ui.footer_html(_t), unsafe_allow_html=True)

# ─── Placeholders de búsqueda y resultados ────────────────────────────────────
action_placeholder      = st.empty()
workflow_placeholder    = st.empty()
results_placeholder     = st.empty()
empty_state_placeholder = st.empty()

if st.session_state.is_searching:
    with action_placeholder.container():
        st.markdown(f'<h2 class="jh-title">{_t("res_title")}</h2><p class="jh-meta">{_t("searching_notice")}</p>',
                    unsafe_allow_html=True)
        with st.container(horizontal=True):
            if st.button(_t("btn_stop"), key="btn_stop"):
                st.session_state.cancel_search = True
                st.session_state.is_searching  = False
                st.rerun()
            if st.button(_t("btn_stop_config"), type="tertiary", key="btn_stop_config"):
                st.session_state.cancel_search     = True
                st.session_state.cancel_and_config = True
                st.session_state.is_searching      = False
                st.rerun()

# ─── Ejecución de la búsqueda ─────────────────────────────────────────────────
SCRAPE_PER_PORTAL = 40
if st.session_state.run_search:
    st.session_state.run_search    = False
    st.session_state.cancel_search = False
    # is_searching ya fue seteado a True en el wizard antes del rerun
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
    eval_limit        = st.session_state.eval_limit
    profile           = _get_profile() or CandidateProfile()
    prefs = matching.SearchPreferences(
        modalities=set(st.session_state.pref_modalities),
        locations=[l.strip() for l in st.session_state.pref_locations.split(",") if l.strip()],
        job_languages=list(st.session_state.pref_languages),
    )

    st.session_state.result_page     = 0
    st.session_state.result_page_all = 0

    # API key, perfil, preferencias y credenciales viajan por parámetro: el proceso es
    # compartido entre usuarios y nada de esto puede quedar en variables de módulo.
    import scrapers as sc

    def render_workflow_step(step_number, step_title):
        with workflow_placeholder.container():
            with st.container(border=True):
                st.caption(_t("wf_step_label", n=step_number, title=step_title))
                status   = st.empty()
                notice   = st.empty()
                progress = st.empty()
                extra    = st.empty()
        return status, notice, progress, extra

    # ── STEP 1: Scraping ──────────────────────────────────────────────────────
    platform_status, platform_notice, progress_scrape, _ = render_workflow_step(1, _t("wf_step1_title"))
    progress_scrape.progress(0, text=_t("wf_starting"))

    all_jobs    = []
    seen_global = set()
    platforms_enabled = {
        "Remotive":       st.session_state.use_remotive,
        "Arbeitnow":      st.session_state.use_arbeitnow,
        "WeWorkRemotely": st.session_state.use_wwr,
        "Himalayas":      st.session_state.use_himalayas,
        "RemoteOK":       st.session_state.use_remoteok,
        "Jobicy":         st.session_state.use_jobicy,
        "GetOnBoard":     st.session_state.use_getonboard,
        "PuenteTalent":   st.session_state.use_puentetalent,
        "LatoJobs":       st.session_state.use_latojobs,
        "WorkingNomads":  st.session_state.use_workingnomads,
        "TheMuse":        st.session_state.use_themuse,
        "Remote.co":      st.session_state.use_remoteco,
        "Jobspresso":     st.session_state.use_jobspresso,
        "JustJoin.it":    st.session_state.use_justjoinit,
        "AuthenticJobs":  st.session_state.use_authenticjobs,
    }
    enabled_list    = [p for p, v in platforms_enabled.items() if v]
    total_platforms = len(enabled_list)
    scrape_started  = time.monotonic()
    # Tope por portal: acota la duración del scraping. El filtrado fino lo hace matching.py.
    per_portal      = SCRAPE_PER_PORTAL

    for idx, platform_name in enumerate(enabled_list):
        platform_status.info(_t("wf_searching", platform=platform_name))
        try:
            remaining = per_portal
            if platform_name == "Remotive":
                jobs = sc.scrape_remotive(keywords, max_results=remaining)
            elif platform_name == "Arbeitnow":
                jobs = sc.scrape_arbeitnow(keywords, max_results=remaining)
            elif platform_name == "WeWorkRemotely":
                jobs = sc.scrape_weworkremotely(keywords, max_results=remaining)
            elif platform_name == "Himalayas":
                jobs = sc.scrape_himalayas(keywords, max_results=remaining)
            elif platform_name == "RemoteOK":
                jobs = sc.scrape_remoteok(keywords, max_results=remaining)
            elif platform_name == "Jobicy":
                jobs = sc.scrape_jobicy(keywords, max_results=remaining)
            elif platform_name == "GetOnBoard":
                jobs = sc.scrape_getonboard(keywords, max_results=remaining)
            elif platform_name == "PuenteTalent":
                jobs = sc.scrape_puente(keywords, max_results=remaining)
            elif platform_name == "LatoJobs":
                jobs = sc.scrape_latojobs(keywords, max_results=remaining)
            elif platform_name == "WorkingNomads":
                jobs = sc.scrape_workingnomads(keywords, max_results=remaining)
            elif platform_name == "TheMuse":
                jobs = sc.scrape_themuse(keywords, max_results=remaining)
            elif platform_name == "Remote.co":
                jobs = sc.scrape_remoteco(keywords, max_results=remaining)
            elif platform_name == "Jobspresso":
                jobs = sc.scrape_jobspresso(max_results=remaining)
            elif platform_name == "JustJoin.it":
                jobs = sc.scrape_justjoinit(keywords, max_results=remaining)
            elif platform_name == "AuthenticJobs":
                jobs = sc.scrape_authenticjobs(max_results=remaining)
            else:
                jobs = []
            for job in jobs:
                key = f"{job.title.lower()[:40]}|{job.company.lower()[:30]}"
                if key not in seen_global:
                    seen_global.add(key)
                    all_jobs.append(job)
        except Exception as e:
            platform_notice.warning(_t("wf_err_platform", platform=platform_name, error=e))

        completed = idx + 1
        elapsed   = time.monotonic() - scrape_started
        rem_plat  = total_platforms - completed
        eta       = _t("wf_eta", time=format_duration((elapsed / completed) * rem_plat)) if rem_plat > 0 else ""
        progress_scrape.progress(completed / total_platforms, text=_t("wf_src_prog", done=completed, total=total_platforms, eta=eta))

        # ── Check cancelación entre plataformas ───────────────────────────────
        if st.session_state.cancel_search:
            platform_status.warning(_t("wf_stopped", n=completed, jobs=len(all_jobs)))
            break

    if not st.session_state.cancel_search:
        platform_status.success(_t("wf_found", jobs=len(all_jobs), time=format_duration(time.monotonic() - scrape_started)))
    progress_scrape.progress(1.0)

    # ── STEP 2: Matching (filtros → pre-ranking → evaluación por factores) ────
    ai_status, ai_notice, progress_ai, _ = render_workflow_step(2, _t("wf_step2_title"))

    scored_jobs    = []
    top_matches    = []
    st.session_state.run_notice  = None
    st.session_state.scored_jobs = []
    st.session_state.top_matches = []
    st.session_state.funnel      = None

    if not all_jobs:
        st.session_state.run_notice = ("wf_no_jobs", {})
        ai_status.warning(_t("wf_no_jobs"))
        progress_ai.progress(1.0)
    else:
        scoring_started = time.monotonic()
        ai_status.info(_t("wf_preparing", n=eval_limit))
        progress_ai.progress(0, text=_t("wf_starting"))

        def _on_progress(stage, done, total):
            elapsed = time.monotonic() - scoring_started
            remaining = (elapsed / done) * (total - done) if done else 0
            eta = _t("wf_eta", time=format_duration(remaining)) if done < total else ""
            ai_status.info(_t("wf_rechecking" if stage == "recheck" else "wf_evaluating", done=done, total=total))
            progress_ai.progress(done / total, text=_t("wf_ai_prog", done=done, total=total, eta=eta))

        result = matching.match_jobs(
            all_jobs, profile, prefs,
            api_key=gemini_key, model=selected_model, lang=st.session_state.lang,
            top_n=eval_limit, on_progress=_on_progress,
        )
        scored_jobs = result.scored
        top_matches = ai_engine.recommended(scored_jobs, min_score)
        st.session_state.scored_jobs    = scored_jobs
        st.session_state.top_matches    = top_matches
        st.session_state.min_score_last = min_score
        st.session_state.funnel = {
            "found": result.total_found,
            "dups": result.duplicates_removed,
            "excluded": result.excluded,
            "out": result.pre_ranked_out,
            "evaluated": sum(1 for j in scored_jobs if j.evaluated),
            "top_n": eval_limit,
            "emb_failed": result.embeddings_failed,
        }
        if result.stop_reason == "auth":
            st.session_state.run_notice = ("wf_auth_error", {})
        elif result.stop_reason == "quota":
            st.session_state.run_notice = ("wf_quota_stop", {})
        elif not scored_jobs:
            st.session_state.run_notice = ("wf_all_filtered", {})

        if st.session_state.run_notice:
            ai_notice.error(_t(st.session_state.run_notice[0], **st.session_state.run_notice[1]))
        else:
            ai_status.success(_t("wf_scored", top=len(top_matches), total=len(scored_jobs),
                                 time=format_duration(time.monotonic() - scoring_started)))
        progress_ai.progress(1.0)

    # ── STEP 3: Email ─────────────────────────────────────────────────────────
    if send_email and top_matches and email_sender and email_password:
        email_status, _, _, _ = render_workflow_step(3, _t("wf_email_title"))
        try:
            from notifier import send_digest
            email_status.info(_t("wf_email_send", recipient=email_recipient))
            send_digest(
                scored_jobs,
                sender=email_sender, password=email_password,
                recipient=email_recipient, min_score=min_score,
            )
            email_status.success(_t("wf_email_ok", recipient=email_recipient))
        except Exception as e:
            email_status.error(_t("wf_email_err", error=e))

    workflow_placeholder.empty()

    st.session_state.search_done  = True
    st.session_state.is_searching = False
    st.session_state.cancel_search = False
    st.rerun()

# ── Renderizado de resultados ────────────────────────────────────────────────
if st.session_state.search_done and not st.session_state.scored_jobs and st.session_state.get("run_notice"):
    with results_placeholder.container():
        st.warning(_t(st.session_state.run_notice[0], **st.session_state.run_notice[1]))

if st.session_state.search_done and st.session_state.scored_jobs:
    _scored = st.session_state.scored_jobs
    _prof   = _get_profile() or CandidateProfile()

    def _generate_letter(sj):
        if not st.session_state.gemini_key:
            st.info(_t("letter_need_key"), icon="🔑")
            return
        with st.spinner(_t("letter_generating")):
            try:
                sj.cover_letter = ai_engine.generate_cover_letter(
                    sj.job, sj.match_reasons, _prof.to_prompt(),
                    api_key=st.session_state.gemini_key, model=st.session_state.selected_model,
                )
            except Exception as e:
                st.error(_t("letter_error", error=e))

    def _chips(job) -> list[str]:
        out = []
        if job.modality in matching.MODALITIES:
            out.append(_t(f"mod_{job.modality}"))
        if job.seniority in SENIORITY_LEVELS and job.seniority != cand.UNKNOWN:
            out.append(_t(f"sen_{job.seniority}"))
        return out

    def _render_job(sj, idx):
        with st.container(border=True, key=f"job_{idx}"):
            st.markdown(ui.job_card_html(sj, _t, _chips(sj.job)), unsafe_allow_html=True)
            with st.container(horizontal=True):
                if sj.job.url:
                    st.link_button(_t("btn_view"), sj.job.url)
                if sj.evaluated and not sj.cover_letter:
                    if st.button(_t("btn_letter"), key=f"gen_{idx}_{sj.job.id}"):
                        _generate_letter(sj)
            if sj.factors:
                with st.expander(_t("btn_why")):
                    for fname in matching.FACTORS:
                        fs = sj.factors[fname]
                        weight = int(matching.WEIGHTS[fname] * 100)
                        st.markdown(f"**{_t('f_' + fname)}** · {fs.score}/100 · {_t('f_weight', w=weight)}")
                        st.progress(fs.score / 100)
                        if fs.evidence_job:
                            st.caption(f"{_t('f_job')} {fs.evidence_job}")
                        if fs.evidence_cv:
                            st.caption(f"{_t('f_cv')} {fs.evidence_cv}")
                    st.caption(_t("factors_note"))
            if sj.cover_letter:
                with st.expander(_t("cover_letter_expander"), expanded=True):
                    st.text(sj.cover_letter)
                    st.download_button(
                        _t("btn_download_letter"), data=sj.cover_letter,
                        file_name=f"cover_{sj.job.company.replace(' ', '_')}_{sj.job.title[:20].replace(' ', '_')}.txt",
                        mime="text/plain", key=f"dl_{idx}_{sj.job.id}",
                    )

    with results_placeholder.container():
        head_l, head_r = st.columns([3, 1], vertical_alignment="bottom")
        with head_l:
            _meta = " · ".join(x for x in (
                ", ".join(_prof.target_roles[:2]),
                _t(f"sen_{_prof.seniority}") if _prof.seniority != cand.UNKNOWN else "",
                _prof.location if _prof.location != cand.UNKNOWN else "",
            ) if x)
            st.markdown(ui.results_header_html(_t("res_title"), _meta), unsafe_allow_html=True)
        with head_r:
            if st.button(_t("btn_new_search"), type="primary", use_container_width=True):
                _open_wizard(4)

        if st.session_state.get("run_notice"):
            st.warning(_t(st.session_state.run_notice[0], **st.session_state.run_notice[1]))
        _f = st.session_state.get("funnel")
        if _f:
            _ex = _f["excluded"]
            st.markdown('<div class="jh-funnel">' + _t(
                "funnel", found=_f["found"], dups=_f["dups"], filtered=sum(_ex.values()),
                mod=_ex.get("modality", 0), lang=_ex.get("language", 0), loc=_ex.get("location", 0),
                out=_f["out"], n=_f["top_n"], evaluated=_f["evaluated"]) + "</div>", unsafe_allow_html=True)
            if _f.get("emb_failed"):
                st.caption(_t("wf_emb_failed", n=_f["top_n"]))

        f_col, list_col = st.columns([1, 2.8], gap="large")
        with f_col:
            with st.container(border=True):
                _min = st.slider(_t("flt_min"), 0, 100, value=st.session_state.min_score_last, step=5, key="flt_min")
                _rec = ai_engine.recommended(_scored, _min)
                _show = st.segmented_control(
                    _t("flt_show"), ["rec", "all"], required=True, default="rec", key="flt_show",
                    format_func=lambda v: _t("show_rec", n=len(_rec)) if v == "rec" else _t("show_all", n=len(_scored)),
                )
                _mods = st.pills(_t("flt_modality"), list(matching.MODALITIES), selection_mode="multi",
                                 format_func=lambda m: _t(f"mod_{m}"), key="flt_mod")
                _lvls = st.pills(_t("flt_level"), ["intern", "junior", "mid", "senior", "lead"], selection_mode="multi",
                                 format_func=lambda v: _t(f"sen_{v}"), key="flt_lvl")

        # Filtros de vista: igual que los duros, un dato desconocido nunca oculta una oferta.
        _list = _rec if _show == "rec" else _scored
        _list = [sj for sj in _list
                 if (not _mods or sj.job.modality == normalize.UNKNOWN or sj.job.modality in _mods)
                 and (not _lvls or sj.job.seniority == normalize.UNKNOWN or sj.job.seniority in _lvls)]

        with list_col:
            if not _list:
                if _show == "rec" and not _rec:
                    st.info(_t("no_recommended", score=_min) if any(s.evaluated for s in _scored) else _t("none_evaluated"))
                else:
                    st.info(_t("res_empty_filter"))
            PAGE_SIZE = 15
            _pages = max(1, -(-len(_list) // PAGE_SIZE))
            _page  = min(st.session_state.result_page, _pages - 1)
            for i, sj in enumerate(_list[_page * PAGE_SIZE:(_page + 1) * PAGE_SIZE]):
                _render_job(sj, _page * PAGE_SIZE + i)
            if _pages > 1:
                p_l, p_c, p_r = st.columns([1, 2, 1], vertical_alignment="center")
                with p_l:
                    if st.button(_t("btn_prev"), disabled=_page == 0, use_container_width=True, key="pg_prev"):
                        st.session_state.result_page = _page - 1
                        st.rerun()
                with p_c:
                    st.caption(_t("page_of", page=_page + 1, pages=_pages))
                with p_r:
                    if st.button(_t("btn_next"), disabled=_page >= _pages - 1, use_container_width=True, key="pg_next"):
                        st.session_state.result_page = _page + 1
                        st.rerun()

            # Exportación desde la sesión del usuario (nunca desde disco compartido).
            _export = [
                {
                    "score":          sj.score if sj.evaluated else None,
                    "evaluated":      sj.evaluated,
                    "title":          sj.job.title,
                    "company":        sj.job.company,
                    "source":         sj.job.source,
                    "url":            sj.job.url,
                    "location":       sj.job.location,
                    "remote":         sj.job.remote,
                    "match_reasons":  sj.match_reasons,
                    "missing_skills": sj.missing_skills,
                    "summary":        sj.summary,
                    "factors":        {k: vars(v) for k, v in sj.factors.items()} if sj.factors else None,
                    "detected":       {"language": sj.job.language, "seniority": sj.job.seniority,
                                       "modality": sj.job.modality},
                    "cover_letter":   sj.cover_letter,
                }
                for sj in _scored
            ]
            st.download_button(
                _t("res_export"), data=json.dumps(_export, ensure_ascii=False, indent=2),
                file_name=f"jobhunter_{datetime.now().strftime('%Y%m%d_%H%M')}.json", mime="application/json",
            )
