"""
web/wizard.py — Asistente de búsqueda en 4 pasos (docs/design/mockup-wizard.html).

1 Tu CV → 2 Acceso a la IA → 3 Tu perfil → 4 Tu búsqueda. No se saltean pasos (Session.max_step).
Se trabaja sobre la sesión (web/session.py) y cada cambio se guarda en la cuenta (web/persist.py):
el CV en el almacenamiento privado, el perfil y las preferencias en la base. La clave de Gemini y la
contraseña de correo quedan solo en la sesión. El CV nunca se escribe en el disco del servidor.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

import ai_engine
import candidate as cand
import demo
import normalize
from candidate import CandidateProfile
from web import auth, persist, portals, run, settings
from web.common import LEVELS, format_date, prefs, render, sess, t_for
from web.persist import StoreError
from web.session import CVFile, Session

log = logging.getLogger("jobhunter.wizard")
router = APIRouter()

MAX_CV_BYTES = settings.MAX_CV_BYTES
CV_TYPES = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
    ".txt": ("text/plain", b""),
}
JOB_LANGUAGES = ("es", "en", "pt", "de", "fr")
_LANG_NAME_HINTS = {
    "es": ("espa", "castellano", "spanish"),
    "en": ("ingl", "english"),
    "pt": ("portug",),
    "de": ("alem", "german", "deutsch"),
    "fr": ("franc", "french"),
}
MAX_TERMS = 20
MAX_TEXT = 4000
MAX_EVAL = 200


# ─── Helpers ─────────────────────────────────────────────────────────────────
def job_lang_codes(p: CandidateProfile) -> list[str]:
    """Idiomas de oferta sugeridos según el CV (el usuario los puede cambiar)."""
    names = [normalize.strip_accents(lang.language.lower()) for lang in p.languages]
    return [code for code, hints in _LANG_NAME_HINTS.items()
            if p.cv_language == code or any(h in n for n in names for h in hints)]


def lang_label(lang: cand.Language) -> str:
    return f"{lang.language} ({lang.level})" if lang.level and lang.level != cand.UNKNOWN else lang.language


def parse_lang_label(label: str) -> cand.Language:
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", label)
    return cand.Language(m.group(1).strip(), m.group(2).strip()) if m else cand.Language(label.strip())


def clean_list(values: list[str], limit: int = 40, max_len: int = 80) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        v = " ".join((v or "").split())[:max_len]
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out[:limit]


def is_structured(p: CandidateProfile | None) -> bool:
    return bool(p and (p.summary or p.target_roles or p.skills or p.experiences))


# ─── La cuenta ───────────────────────────────────────────────────────────────
def to_account(request: Request, write) -> bool:
    """Guarda en la cuenta con `write(store, user)`. La sesión ya tiene el cambio: si la base no
    responde se devuelve False para avisarlo, y el próximo guardado lo vuelve a intentar."""
    store, user = persist.get(), auth.current_user(request)
    if store is None or user is None:
        return True
    try:
        write(store, user)
        return True
    except StoreError:
        log.warning("wizard: no se pudo guardar en la cuenta", exc_info=True)
        return False


def save_profile_row(request: Request, s: Session) -> bool:
    if s.profile is None:
        return True
    source = "manual" if s.manual_profile else "cv"
    return to_account(request, lambda st, u: st.save_profile(
        u, s.profile.to_dict(), confirmed=s.profile_confirmed, source=source, cv_id=s.cv_doc_id or None))


def save_prefs_row(request: Request, s: Session) -> bool:
    return to_account(request, lambda st, u: st.save_preferences(u, {
        "terms": s.terms, "modalities": s.modalities, "locations": s.locations, "job_languages": s.job_languages,
        "portals": s.portals, "min_score": s.min_score, "eval_limit": s.eval_limit}))


def limits(s: Session) -> dict:
    """Topes del plan para el paso 4 (None = sin tope)."""
    plan = s.plan
    return {"portals": getattr(plan, "sources_per_search_limit", None),
            "eval": getattr(plan, "results_per_search_limit", None),
            "monthly": getattr(plan, "monthly_search_limit", None)}


def fit_to_plan(s: Session) -> None:
    """La selección por defecto (o una guardada con otro plan) nunca pasa los topes del plan."""
    lim = limits(s)
    if lim["portals"] is not None:
        s.portals = s.portals[:lim["portals"]]
    if lim["eval"] is not None:
        s.eval_limit = min(s.eval_limit, lim["eval"])


def usage(request: Request) -> dict | None:
    """Búsquedas usadas este mes y cuándo se renueva el cupo."""
    s, store, user = sess(request), persist.get(), auth.current_user(request)
    monthly = limits(s)["monthly"]
    if store is None or user is None or monthly is None:
        return None
    try:
        used = store.searches_used(user)
    except StoreError:
        return None
    return {"used": used, "limit": monthly, "left": max(0, monthly - used), "renews": persist.next_month_start()}


def cv_data(request: Request, s: Session) -> bytes:
    """Los bytes del CV: en la sesión si se acaba de subir; si no, del almacenamiento de la cuenta."""
    if s.cv and s.cv.data:
        return s.cv.data
    store, user = persist.get(), auth.current_user(request)
    data = store.cv_bytes(user) if store is not None and user is not None else None
    if not data:
        raise StoreError("cv file missing")
    s.cv.data = data
    return data


# Duración real de las últimas búsquedas (en memoria del proceso; la etapa 3 las registra con record_run).
_RUN_MINUTES: list[float] = []


def record_run(minutes: float, eval_limit: int) -> None:
    """Guarda cuánto tardó una búsqueda real, por oferta evaluada, para afinar la estimación."""
    if eval_limit > 0 and minutes > 0:
        _RUN_MINUTES.append(minutes / eval_limit)
        del _RUN_MINUTES[:-20]


def estimate_minutes(eval_limit: int, n_portals: int) -> tuple[int, int]:
    """Rango estimado (mínimo, máximo) en minutos: leer los portales + evaluar con IA.

    Con búsquedas reales registradas se usa su promedio; si no, el ritmo del limitador de Gemini
    (evaluación híbrida: un lote cada 5 ofertas + un re-chequeo de las 10 mejores).
    """
    if len(_RUN_MINUTES) >= 3:
        per_listing = sum(_RUN_MINUTES) / len(_RUN_MINUTES)
        base = per_listing * eval_limit
    else:
        scraping = 0.15 * n_portals          # ~9 s por portal; alguno (Get on Board) tarda bastante más
        calls = math.ceil(eval_limit / 5) + min(10, eval_limit) + 1
        base = scraping + calls / ai_engine.REQUESTS_PER_MINUTE
    return max(1, math.ceil(base)), max(2, math.ceil(base * 1.7))


def verify_key(key: str, model: str) -> bool | None:
    # Modo demo (solo desarrollo): sin llamadas a Gemini.
    if demo.enabled():
        return key.startswith("AIza")
    return ai_engine.check_key(key, model)


def analyze_cv(request: Request, s: Session) -> CandidateProfile:
    if demo.enabled():
        return demo.load()[0]
    contents = cand.cv_contents(cv_data(request, s), s.cv.mime)
    return cand.extract_profile(contents, api_key=s.api_key, model=s.model)


def model_label(model: str) -> str:
    """"models/gemini-3.5-flash-lite" → "Gemini 3.5 Flash Lite"."""
    return " ".join(w.capitalize() for w in model.removeprefix("models/").split("-"))


def review_items(p: CandidateProfile, t) -> list[tuple[str, str]]:
    """Datos que conviene completar en el paso 3: (texto, id del campo)."""
    items = []
    if not p.target_roles:
        items.append((t("wz_attn_roles"), "f-roles"))
    if p.seniority == cand.UNKNOWN:
        items.append((t("wz_attn_level"), "f-level"))
    if p.years_experience is None:
        items.append((t("wz_attn_years"), "f-years"))
    if p.location == cand.UNKNOWN:
        items.append((t("wz_attn_location"), "f-location"))
    for lang in p.languages:
        if not lang.level or lang.level == cand.UNKNOWN:
            items.append((t("wz_attn_lang_level", lang=lang.language), "f-langs"))
    return items


def rail(s: Session, t) -> list[dict]:
    """Panel lateral: estado y resumen de cada paso."""
    p = s.profile
    prof_bits = []
    if p is not None and is_structured(p):
        prof_bits = [x for x in (p.target_roles[0] if p.target_roles else "",
                                 t(f"sen_{p.seniority}") if p.seniority != cand.UNKNOWN else "",
                                 p.location if p.location != cand.UNKNOWN else "") if x]
    return [
        {"title": t("wz1"), "sub": s.cv.name if s.cv else (t("wz_rail_manual") if s.manual_profile else t("wz_rail1"))},
        {"title": t("wz2"), "sub": t("wz_rail2_done") if s.api_key and s.key_ok else t("wz_rail2")},
        {"title": t("wz3"), "sub": " · ".join(prof_bits) if prof_bits else t("wz_rail3")},
        {"title": t("wz4"), "sub": t("wz_rail4")},
    ]


def page(request: Request, step: int, status_code: int = 200, **ctx) -> HTMLResponse:
    s, t = sess(request), t_for(request)
    notice = t("wz_session_expired") if (getattr(request.state, "session_expired", False)
                                         or request.query_params.get("sesion") == "vencida") else None
    masked = f"{s.api_key[:4]}…{s.api_key[-4:]}" if len(s.api_key) > 12 else ""
    return render(request, "wizard.html", status_code=status_code, step=step, max_step=s.max_step(),
                  rail=rail(s, t), s=s, notice=notice, masked_key=masked, **ctx)


def go(step: int, **query) -> RedirectResponse:
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    return RedirectResponse(f"/asistente/{step}" + (f"?{qs}" if qs else ""), status_code=303)


# ─── Navegación ──────────────────────────────────────────────────────────────
@router.get("/asistente")
def wizard_start(request: Request):
    notice = {"sesion": "vencida"} if request.query_params.get("sesion") == "vencida" else {}
    return go(sess(request).max_step(), **notice)


@router.get("/asistente/{step}", response_class=HTMLResponse)
def wizard_step(request: Request, step: int):
    s = sess(request)
    if step < 1 or step > 4:
        return go(1)
    if step > s.max_step():
        return go(s.max_step())
    return page(request, step, **step_context(request, step))


def step_context(request: Request, step: int) -> dict:
    s, t = sess(request), t_for(request)
    if step == 2:
        return {"models": ai_engine.AVAILABLE_MODELS, "model_label": model_label,
                "needs_analysis": bool(s.cv) and s.analyzed_cv_id != s.cv.id}
    if step == 3:
        p = s.profile or CandidateProfile()
        return {"p": p, "structured": is_structured(p), "levels": LEVELS,
                "langs": [lang_label(x) for x in p.languages],
                "unknown_langs": {lang_label(x) for x in p.languages if not x.level or x.level == cand.UNKNOWN},
                "skill_evidence": {sk.name.lower(): sk.evidence for sk in p.skills if sk.evidence},
                "review": review_items(p, t) if is_structured(p) else []}
    if step == 4:
        p = s.profile or CandidateProfile()
        tagged = {term.lower(): lang for lang, terms in p.search_terms.items() for term in terms}
        n_portals = len([k for k in s.portals if k in portals.BY_KEY])
        low, high = estimate_minutes(s.eval_limit, n_portals)
        mode_text = ", ".join(t(f"mod_{m}") for m in s.modalities) or t("pref_any")
        lim = limits(s)
        return {"groups": portals.grouped(s.portals), "tagged": tagged, "job_langs": JOB_LANGUAGES,
                "est_low": low, "est_high": high, "n_portals": n_portals, "mode_text": mode_text,
                "rpm": ai_engine.REQUESTS_PER_MINUTE, "max_portals": lim["portals"],
                "max_eval": lim["eval"] or MAX_EVAL, "usage": usage(request)}
    return {}


# Campos con error visible en cada paso (para responder solo el error, sin redibujar la pantalla).
ERROR_FIELDS = {
    2: ["key", "email_sender", "email_recipient", "email_password"],
    3: ["notes"],
    4: ["terms", "portal"],
}


def invalid(request: Request, step: int, errors: dict, status_code: int = 400, **ctx):
    """Errores de validación: por HTMX se actualizan solo las líneas de error; si no, se redibuja el paso."""
    if request.headers.get("HX-Request") and all(k in ERROR_FIELDS.get(step, []) for k in errors):
        return render(request, "_field_errors.html", errors=errors, fields=ERROR_FIELDS[step],
                      headers={"HX-Reswap": "none transition:false"})
    return page(request, step, status_code=status_code, errors=errors, **ctx)


# ─── Sesión vencida ──────────────────────────────────────────────────────────
def expired(request: Request):
    """Si la sesión en memoria venció (o el servidor se reinició), lo guardado en la cuenta ya se
    recargó, pero no la clave de Gemini: volver al paso que corresponda explicando por qué."""
    if not getattr(request.state, "session_expired", False):
        return None
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": "/asistente?sesion=vencida"})
    return RedirectResponse("/asistente?sesion=vencida", status_code=303)


# ─── Formularios → sesión (lo usan el envío y el guardado automático) ────────
def apply_ai_form(s: Session, form) -> None:
    model = str(form.get("model", s.model))
    s.model = model if model in ai_engine.AVAILABLE_MODELS else ai_engine.DEFAULT_MODEL
    s.send_email = bool(form.get("send_email"))
    s.email_sender = str(form.get("email_sender", "")).strip()[:200]
    s.email_recipient = str(form.get("email_recipient", "")).strip()[:200]
    password = str(form.get("email_password", "")).strip()
    if password:
        s.email_password = password[:40]


def apply_profile_form(s: Session, form, t) -> None:
    p = s.profile or CandidateProfile()
    p.notes = str(form.get("notes", ""))[:MAX_TEXT].strip()
    if is_structured(p) or "summary" in form:
        p.summary = str(form.get("summary", ""))[:MAX_TEXT].strip()
        p.target_roles = clean_list(form.getlist("roles"))
        level = str(form.get("seniority", cand.UNKNOWN))
        p.seniority = level if level in cand.SENIORITY_LEVELS else cand.UNKNOWN
        years = str(form.get("years", "")).replace(",", ".").strip()
        try:
            p.years_experience = max(0.0, min(60.0, float(years))) if years else None
        except ValueError:
            p.years_experience = None
        p.location = " ".join(str(form.get("location", "")).split())[:120] or cand.UNKNOWN
        p.languages = [parse_lang_label(x) for x in clean_list(form.getlist("langs"))]
        evidence = {sk.name.lower(): sk.evidence for sk in p.skills}
        p.skills = [cand.Skill(name=n, evidence=evidence.get(n.lower(), t("prof_added_by_user")))
                    for n in clean_list(form.getlist("skills"), limit=80)]
    s.profile = p


def apply_search_form(s: Session, form) -> None:
    available = {p.key for p in portals.available()}
    s.terms = clean_list(form.getlist("terms"), limit=MAX_TERMS, max_len=60)
    s.modalities = [m for m in form.getlist("modality") if m in ("remote", "hybrid", "onsite")]
    s.locations = " ".join(str(form.get("locations", "")).split())[:200]
    s.job_languages = [c for c in form.getlist("job_lang") if c in JOB_LANGUAGES]
    s.portals = [k for k in form.getlist("portal") if k in available]

    def bounded(name: str, lo: int, hi: int, default: int) -> int:
        try:
            return max(lo, min(hi, int(str(form.get(name, default)))))
        except ValueError:
            return default

    s.min_score = bounded("min_score", 30, 90, s.min_score)
    s.eval_limit = bounded("eval_limit", 10, limits(s)["eval"] or MAX_EVAL, s.eval_limit)


@router.post("/asistente/borrador/{step}")
async def save_draft(request: Request, step: int):
    """Guardado automático mientras se edita (sin validar): cambiar de idioma, recargar o volver
    atrás nunca pierde lo escrito."""
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    if step > s.max_step() or step not in (1, 2, 3, 4):
        return Response(status_code=204)
    form = await request.form()
    saved = True
    if step == 1:
        if s.manual_profile and "notes" in form:
            s.profile = s.profile or CandidateProfile()
            s.profile.notes = str(form.get("notes", ""))[:MAX_TEXT].strip()
            saved = save_profile_row(request, s)
    elif step == 2:
        apply_ai_form(s, form)       # clave, modelo y correo: solo en la sesión
    elif step == 3:
        apply_profile_form(s, form, t_for(request))
        saved = save_profile_row(request, s)
    else:
        apply_search_form(s, form)
        saved = save_prefs_row(request, s)
    return Response(status_code=204 if saved else 503)


# ─── Paso 1: CV ──────────────────────────────────────────────────────────────
@router.post("/asistente/cv")
async def upload_cv(request: Request, cv: UploadFile = File(...), origin: str = Form("")):
    s, t = sess(request), t_for(request)
    ext = Path(cv.filename or "").suffix.lower()
    data = await cv.read(MAX_CV_BYTES + 1)
    error = None
    if ext not in CV_TYPES:
        error = t("wz_err_type")
    elif len(data) > MAX_CV_BYTES:
        error = t("wz_err_size", mb=MAX_CV_BYTES // (1024 * 1024))
    elif not data.strip():
        error = t("wz_err_empty")
    elif not data.startswith(CV_TYPES[ext][1]):
        error = t("wz_err_type")   # la extensión no coincide con el contenido
    if error:
        return page(request, 1, status_code=400, error=error)
    sha = hashlib.sha256(data).hexdigest()
    cv_id = sha[:16]
    name, mime = Path(cv.filename).name[:120], CV_TYPES[ext][0]
    if not (s.cv and s.cv.id == cv_id and s.cv_doc_id):
        # El mismo archivo otra vez no se vuelve a subir; uno distinto reemplaza al vigente.
        doc = {}
        if not to_account(request, lambda st, u: doc.update(id=st.save_cv(u, name=name, mime=mime, data=data, sha=sha))):
            return page(request, 1, status_code=503, error=t("err_store"))
        s.cv_doc_id = doc.get("id", "")
    if cv_id != s.analyzed_cv_id:
        # Otro CV: el perfil y los términos anteriores ya no corresponden.
        s.profile, s.terms, s.job_languages = None, [], []
        s.profile_confirmed = False
    s.cv = CVFile(name=name, mime=mime, data=data, id=cv_id, size=len(data))
    s.manual_profile = False
    return go(2) if origin == "landing" else go(1, listo=1)


@router.post("/asistente/cv/quitar")
def remove_cv(request: Request):
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    if not to_account(request, lambda st, u: st.delete_cv(u)):
        return page(request, 1, status_code=503, error=t_for(request)("err_store"))
    s.cv, s.cv_doc_id = None, ""
    return go(1)


@router.post("/asistente/manual")
async def manual_profile(request: Request):
    """Perfil escrito a mano, en el mismo paso 1. Sin texto (viene de la landing): abre el editor."""
    if (r := expired(request)) is not None:
        return r
    s, t = sess(request), t_for(request)
    form = await request.form()
    notes = str(form.get("notes", ""))[:MAX_TEXT].strip()
    if s.cv or is_structured(s.profile):
        # El perfil anterior venía de un CV: se empieza de cero. El CV guardado se borra: escribir el
        # perfil a mano lo reemplaza, y no se guarda un archivo que ya no se usa.
        if s.cv and not to_account(request, lambda st, u: st.delete_cv(u)):
            return page(request, 1, status_code=503, error=t("err_store"))
        s.profile, s.terms, s.job_languages, s.analyzed_cv_id = None, [], [], ""
    s.cv, s.cv_doc_id, s.manual_profile = None, "", True
    if "notes" not in form:
        return go(1, escribir=1)
    if not notes:
        return page(request, 1, status_code=400, error=t("wz_err_manual_empty"))
    s.profile = s.profile or CandidateProfile()
    s.profile.notes = notes
    s.profile_confirmed = False
    if not save_profile_row(request, s):
        return page(request, 1, status_code=503, error=t("err_store"))
    return go(2)


# ─── Paso 2: acceso a la IA ──────────────────────────────────────────────────
@router.post("/asistente/clave", response_class=HTMLResponse)
def check_key(request: Request, key: str = Form(""), model: str = Form(ai_engine.DEFAULT_MODEL)):
    """Fragmento HTMX: estado de la clave + botón principal (fuera de banda)."""
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    key = key.strip()
    result = verify_key(key, model if model in ai_engine.AVAILABLE_MODELS else ai_engine.DEFAULT_MODEL) if key else False
    # Se guarda también cuando Google la rechaza: así cambiar de idioma o recargar no obliga a volver a pegarla.
    if key:
        s.api_key, s.key_ok = key, result
    return render(request, "_wz_key_status.html", key_state=result, typed=bool(key), s=s,
                  needs_analysis=bool(s.cv) and s.analyzed_cv_id != s.cv.id)


@router.post("/asistente/clave/cambiar")
def change_key(request: Request):
    """Borra la clave guardada. Por HTMX se reemplaza solo ese campo: el paso no se redibuja."""
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    s.api_key, s.key_ok = "", None
    if request.headers.get("HX-Request"):
        return render(request, "_wz_key_field.html", s=s, masked_key="", errors={},
                      needs_analysis=bool(s.cv) and s.analyzed_cv_id != s.cv.id)
    return go(2)


@router.post("/asistente/ia")
async def save_ai(request: Request):
    if (r := expired(request)) is not None:
        return r
    s, t = sess(request), t_for(request)
    if s.max_step() < 2:
        return go(1)
    form = await request.form()
    apply_ai_form(s, form)
    key = str(form.get("key", "")).strip() or s.api_key

    errors = {}
    if not key:
        ok = False
    elif key != s.api_key or s.key_ok is None:
        ok = verify_key(key, s.model)
    else:
        ok = s.key_ok
    if ok is False:
        errors["key"] = t("wz_err_key")
    else:
        s.api_key, s.key_ok = key, ok
    if s.send_email:
        if "@" not in s.email_sender:
            errors["email_sender"] = t("val_email")
        if "@" not in s.email_recipient:
            errors["email_recipient"] = t("val_recip")
        if len(s.email_password.replace(" ", "")) != 16:
            errors["email_password"] = t("val_pass")
    if errors:
        return invalid(request, 2, errors, **step_context(request, 2))

    if s.cv and s.analyzed_cv_id != s.cv.id:
        try:
            profile = analyze_cv(request, s)
        except StoreError:
            return page(request, 2, status_code=503, errors={"_": t("err_store")}, **step_context(request, 2))
        except ai_engine.AuthError:
            s.api_key, s.key_ok = "", False
            return page(request, 2, status_code=400, errors={"key": t("wz_err_key")}, **step_context(request, 2))
        except ai_engine.QuotaExceeded:
            return page(request, 2, status_code=429, errors={"_": t("wz_err_quota")}, **step_context(request, 2))
        except Exception:  # noqa: BLE001 — nunca mostrar la excepción cruda al usuario
            return page(request, 2, status_code=502, errors={"_": t("wz_err_analyze")}, **step_context(request, 2))
        s.profile = profile
        s.profile_confirmed = False
        s.analyzed_cv_id = s.cv.id
        s.terms = profile.all_search_terms()
        s.job_languages = job_lang_codes(profile)
        parsed = profile.to_dict()
        model = "demo" if demo.enabled() else s.model
        # La lectura de la IA queda junto al CV, con el modelo que la hizo (spec §10).
        to_account(request, lambda st, u: st.mark_cv_parsed(u, s.cv_doc_id, parsed, model))
        save_profile_row(request, s)
        save_prefs_row(request, s)
    elif s.profile is None:
        s.profile = CandidateProfile()
    return go(3)


# ─── Paso 3: perfil ──────────────────────────────────────────────────────────
@router.post("/asistente/perfil")
async def save_profile(request: Request):
    if (r := expired(request)) is not None:
        return r
    s, t = sess(request), t_for(request)
    if s.max_step() < 3:
        return go(s.max_step())
    apply_profile_form(s, await request.form(), t)
    if s.profile.is_empty():
        return invalid(request, 3, {"notes": t("step4_warning")}, **step_context(request, 3))
    s.profile_confirmed = True
    if not save_profile_row(request, s):
        return page(request, 3, status_code=503, errors={"_": t("err_store")}, **step_context(request, 3))
    return go(4)


# ─── Paso 4: búsqueda ────────────────────────────────────────────────────────
@router.post("/asistente/busqueda")
async def save_search(request: Request):
    if (r := expired(request)) is not None:
        return r
    s, t = sess(request), t_for(request)
    if s.max_step() < 4:
        return go(s.max_step())
    apply_search_form(s, await request.form())
    errors = {}
    max_portals = limits(s)["portals"]
    if not s.terms:
        errors["terms"] = t("val_no_kw")
    if not s.portals:
        errors["portal"] = t("wz_err_portals")
    elif max_portals is not None and len(s.portals) > max_portals:
        errors["portal"] = t("wz_err_portals_max", n=max_portals)
    if errors:
        return invalid(request, 4, errors, **step_context(request, 4))
    save_prefs_row(request, s)
    try:
        run.start(s, prefs(request)[0])
    except run.MonthlyLimit:
        u = usage(request) or {}
        renews = u.get("renews") or persist.next_month_start()
        return page(request, 4, status_code=429, **step_context(request, 4), errors={
            "_": t("wz_err_monthly", n=limits(s)["monthly"], date=format_date(t, renews))})
    except StoreError:
        return page(request, 4, status_code=503, errors={"_": t("err_store")}, **step_context(request, 4))
    return RedirectResponse("/buscando", status_code=303)


@router.get("/buscando", response_class=HTMLResponse)
def searching(request: Request):
    """Pantalla de progreso. El trabajo corre en su hilo (web/run.py); acá solo se lee su estado."""
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    if s.run is None:
        return go(s.max_step())
    if s.run.outcome in (run.SUCCESS, run.PARTIAL):
        s.history_view = None   # lo recién buscado va antes que una búsqueda vieja abierta mientras tanto
        return RedirectResponse("/resultados", status_code=303)
    return render(request, "searching.html", s=s, run=s.run)


def run_state(request: Request):
    """Estado actual de la corrida: el fragmento, o el camino a los resultados si ya terminó bien."""
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    if s.run is None:
        return go(s.max_step())
    if s.run.outcome in (run.SUCCESS, run.PARTIAL):
        s.history_view = None
        if request.headers.get("HX-Request"):
            return Response(status_code=204, headers={"HX-Redirect": "/resultados"})
        return RedirectResponse("/resultados", status_code=303)
    return render(request, "_run.html", s=s, run=s.run)


@router.get("/buscando/estado", response_class=HTMLResponse)
def searching_state(request: Request):
    """Se pide una vez por segundo mientras la búsqueda corre."""
    return run_state(request)


@router.post("/buscando/detener")
def stop_search(request: Request):
    """Detener corta entre portales o al terminar la tanda de evaluación en curso."""
    s = sess(request)
    if s.run is not None:
        s.run.cancel()
    if not request.headers.get("HX-Request"):
        return RedirectResponse("/buscando", status_code=303)
    return run_state(request)
