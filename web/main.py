"""
web/main.py — Interfaz web de JobHunter (FastAPI + Jinja2 + HTMX).

Reemplaza de a poco a la UI de Streamlit (app.py), que sigue desplegada hasta tener paridad.
Etapa 1: landing y resultados (datos de demo.py con JOB_HUNTER_DEMO=1).
Etapa 2: asistente de 4 pasos (web/wizard.py).

Local:  uvicorn web.main:app --reload --port 8600
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import ai_engine
import candidate as cand
import demo
import matching
import normalize
from web import portals, wizard
from web import session as sessions
from web.common import BRAND, LEVELS, ROOT, prefs, render, translator
# Reexportados para los tests y plantillas existentes.
from web.common import affinity, avatar_color, dom_id, safe_url  # noqa: F401

PAGE_SIZE = 15
DEFAULT_MIN_SCORE = 65
N_PORTALS = len(portals.available())

app = FastAPI(title="JobHunter", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/brand", StaticFiles(directory=BRAND / "logo"), name="brand")
app.include_router(wizard.router)

CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def session_and_headers(request: Request, call_next):
    sid, sess, is_new = sessions.get(request.cookies.get(sessions.COOKIE))
    request.state.session = sess
    response = await call_next(request)
    if is_new and not request.url.path.startswith(("/static", "/brand")):
        response.set_cookie(sessions.COOKIE, sid, httponly=True, samesite="lax", secure=request.url.scheme == "https",
                            max_age=sessions.TTL_SECONDS)
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# ─── Datos de resultados ─────────────────────────────────────────────────────
# Etapa 1: solo demo. En la etapa 3 esto sale de la búsqueda de la sesión del usuario.
@lru_cache(maxsize=1)
def demo_results():
    profile, scored = demo.load()
    funnel = {"found": 112, "dups": 6, "excluded": {"modality": 9, "language": 4, "location": 3},
              "out": 50, "evaluated": len(scored), "top_n": 40}
    return profile, scored, funnel


def current_results():
    return demo_results() if demo.enabled() else None


def chips(job, t) -> list[str]:
    out = []
    if job.modality in matching.MODALITIES:
        out.append(t(f"mod_{job.modality}"))
    if job.seniority in LEVELS:
        out.append(t(f"sen_{job.seniority}"))
    return out


def filtered(scored, show: str, min_score: int, mods: list[str], lvls: list[str]):
    """Filtros de vista: igual que los filtros duros, un dato desconocido nunca oculta una oferta."""
    rec = ai_engine.recommended(scored, min_score)
    base = scored if show == "all" else rec
    jobs = [sj for sj in base
            if (not mods or sj.job.modality == normalize.UNKNOWN or sj.job.modality in mods)
            and (not lvls or sj.job.seniority == normalize.UNKNOWN or sj.job.seniority in lvls)]
    return jobs, rec


def read_filters(request: Request) -> dict:
    q = request.query_params
    try:
        min_score = max(0, min(100, int(q.get("min", DEFAULT_MIN_SCORE))))
    except ValueError:
        min_score = DEFAULT_MIN_SCORE
    try:
        page = max(0, int(q.get("page", 0)))
    except ValueError:
        page = 0
    return {
        "show": "all" if q.get("show") == "all" else "rec",
        "min": min_score,
        "mods": [m for m in q.getlist("mod") if m in matching.MODALITIES],
        "lvls": [v for v in q.getlist("lvl") if v in LEVELS],
        "page": page,
    }


def list_context(scored, f: dict) -> dict:
    jobs, rec = filtered(scored, f["show"], f["min"], f["mods"], f["lvls"])
    pages = max(1, -(-len(jobs) // PAGE_SIZE))
    page = min(f["page"], pages - 1)
    return {
        "jobs": jobs[page * PAGE_SIZE:(page + 1) * PAGE_SIZE], "n_rec": len(rec), "n_all": len(scored),
        "any_evaluated": any(sj.evaluated for sj in scored), "page": page, "pages": pages, "f": f,
        "chips": chips, "factors": matching.FACTORS, "weights": matching.WEIGHTS,
    }


# ─── Rutas ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return render(request, "landing.html", n_portals=N_PORTALS, has_results=current_results() is not None)


@app.get("/empezar")
def start():
    return RedirectResponse("/asistente", status_code=303)


@app.get("/resultados", response_class=HTMLResponse)
def results(request: Request):
    data = current_results()
    if not data:
        return RedirectResponse("/", status_code=303)
    profile, scored, funnel = data
    t = translator(prefs(request)[0])
    meta = " · ".join(x for x in (
        ", ".join(profile.target_roles[:2]),
        t(f"sen_{profile.seniority}") if profile.seniority != cand.UNKNOWN else "",
        profile.location if profile.location != cand.UNKNOWN else "",
    ) if x)
    return render(request, "results.html", meta=meta, funnel=funnel, levels=LEVELS,
                  modalities=matching.MODALITIES, **list_context(scored, read_filters(request)))


@app.get("/resultados/lista", response_class=HTMLResponse)
def results_list(request: Request):
    """Fragmento HTMX: la lista filtrada (y los contadores, fuera de banda)."""
    data = current_results()
    if not data:
        return HTMLResponse("", status_code=204)
    return render(request, "_list.html", **list_context(data[1], read_filters(request)))


@app.post("/carta/{job_id}", response_class=HTMLResponse)
def cover_letter(request: Request, job_id: str):
    # Etapa 3: generar con la key de la sesión. Hoy no hay sesión con acceso a la IA.
    t = translator(prefs(request)[0])
    return HTMLResponse(f'<p class="note-inline">{t("letter_need_key")}</p>')


@app.get("/resultados/export.json")
def export(request: Request):
    data = current_results()
    if not data:
        return RedirectResponse("/", status_code=303)
    payload = [{
        "score": sj.score if sj.evaluated else None, "evaluated": sj.evaluated,
        "title": sj.job.title, "company": sj.job.company, "source": sj.job.source, "url": sj.job.url,
        "location": sj.job.location, "remote": sj.job.remote,
        "match_reasons": sj.match_reasons, "missing_skills": sj.missing_skills, "summary": sj.summary,
        "factors": {k: vars(v) for k, v in sj.factors.items()} if sj.factors else None,
        "detected": {"language": sj.job.language, "seniority": sj.job.seniority, "modality": sj.job.modality},
        "cover_letter": sj.cover_letter,
    } for sj in data[1]]
    name = f"jobhunter_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    return Response(json.dumps(payload, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
