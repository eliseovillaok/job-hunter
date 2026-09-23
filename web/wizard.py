"""
web/wizard.py — Asistente de búsqueda en 4 pasos (docs/design/mockup-wizard.html).

1 Tu CV → 2 Acceso a la IA → 3 Tu perfil → 4 Tu búsqueda. No se saltean pasos (Session.max_step).
Todo queda en la sesión del usuario (web/session.py); el CV nunca se escribe en disco.
"""

from __future__ import annotations

import hashlib
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
from web import portals, settings
from web.common import LEVELS, render, sess, t_for
from web.session import CVFile, Session

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


def estimate_minutes(eval_limit: int, n_portals: int) -> int:
    """Estimación gruesa: lectura de portales + llamadas a Gemini al ritmo del limitador (evaluación híbrida)."""
    scraping = 0.12 * n_portals
    calls = math.ceil(eval_limit / 5) + min(10, eval_limit) + 1
    return max(1, math.ceil(scraping + calls / ai_engine.REQUESTS_PER_MINUTE))


def verify_key(key: str, model: str) -> bool | None:
    # Modo demo (solo desarrollo): sin llamadas a Gemini.
    if demo.enabled():
        return key.startswith("AIza")
    return ai_engine.check_key(key, model)


def analyze_cv(s: Session) -> CandidateProfile:
    if demo.enabled():
        return demo.load()[0]
    contents = cand.cv_contents(s.cv.data, s.cv.mime)
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
    return go(sess(request).max_step())


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
        return {"groups": portals.grouped(s.portals), "tagged": tagged, "job_langs": JOB_LANGUAGES,
                "estimate": estimate_minutes(s.eval_limit, n_portals), "n_portals": n_portals,
                "rpm": ai_engine.REQUESTS_PER_MINUTE}
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
    """Si la sesión venció (o el servidor se reinició), volver al paso 1 explicando por qué."""
    if not getattr(request.state, "session_expired", False):
        return None
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": "/asistente/1?sesion=vencida"})
    return go(1, sesion="vencida")


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
    s.eval_limit = bounded("eval_limit", 10, 200, s.eval_limit)


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
    if step == 1:
        if s.manual_profile and "notes" in form:
            s.profile = s.profile or CandidateProfile()
            s.profile.notes = str(form.get("notes", ""))[:MAX_TEXT].strip()
    elif step == 2:
        apply_ai_form(s, form)
    elif step == 3:
        apply_profile_form(s, form, t_for(request))
    else:
        apply_search_form(s, form)
    return Response(status_code=204)


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
    cv_id = hashlib.sha256(data).hexdigest()[:16]
    if cv_id != s.analyzed_cv_id:
        # Otro CV: el perfil y los términos anteriores ya no corresponden.
        s.profile, s.terms, s.job_languages, s.search_ready = None, [], [], False
        s.profile_confirmed = False
    s.cv = CVFile(name=Path(cv.filename).name[:120], mime=CV_TYPES[ext][0], data=data, id=cv_id)
    s.manual_profile = False
    return go(2) if origin == "landing" else go(1, listo=1)


@router.post("/asistente/cv/quitar")
def remove_cv(request: Request):
    if (r := expired(request)) is not None:
        return r
    sess(request).cv = None
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
        # El perfil anterior venía de un CV: se empieza de cero.
        s.profile, s.terms, s.job_languages, s.analyzed_cv_id = None, [], [], ""
    s.cv, s.manual_profile, s.search_ready = None, True, False
    if "notes" not in form:
        return go(1, escribir=1)
    if not notes:
        return page(request, 1, status_code=400, error=t("wz_err_manual_empty"))
    s.profile = s.profile or CandidateProfile()
    s.profile.notes = notes
    s.profile_confirmed = False
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
    if (r := expired(request)) is not None:
        return r
    s = sess(request)
    s.api_key, s.key_ok = "", None
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
            profile = analyze_cv(s)
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
    if not s.terms:
        errors["terms"] = t("val_no_kw")
    if not s.portals:
        errors["portal"] = t("wz_err_portals")
    if errors:
        return invalid(request, 4, errors, **step_context(request, 4))
    s.search_ready = True
    return RedirectResponse("/buscando", status_code=303)


@router.get("/buscando", response_class=HTMLResponse)
def searching(request: Request):
    # Etapa 3: acá corre la búsqueda en segundo plano con progreso en vivo.
    s = sess(request)
    if not s.search_ready:
        return go(s.max_step())
    return render(request, "searching.html", s=s)
