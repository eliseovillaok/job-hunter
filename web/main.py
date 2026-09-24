"""
web/main.py — Interfaz web de JobHunter (FastAPI + Jinja2 + HTMX).

Reemplaza de a poco a la UI de Streamlit (app.py), que sigue desplegada hasta tener paridad.
Etapa 1: landing y resultados (datos de demo.py con JOB_HUNTER_DEMO=1).
Etapa 2: asistente de 4 pasos (web/wizard.py).

Local:  uvicorn web.main:app --reload --port 8600
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import ai_engine
import candidate as cand
import demo
import matching
import normalize
from web import portals, settings, wizard
from web import session as sessions
from web.common import BRAND, LEVELS, ROOT, prefs, render, sess, translator
# Reexportados para los tests y plantillas existentes.
from web.common import affinity, avatar_color, dom_id, safe_url  # noqa: F401

log = logging.getLogger("jobhunter.web")

PAGE_SIZE = 15
DEFAULT_MIN_SCORE = 65
N_PORTALS = len(portals.available())

app = FastAPI(title="JobHunter", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/brand", StaticFiles(directory=BRAND / "logo"), name="brand")
app.include_router(wizard.router)

# ─── Salud (la plataforma de despliegue consulta estas dos) ──────────────────
@app.get("/health/live", include_in_schema=False)
def health_live():
    """El proceso responde. No toca dependencias: sirve para reiniciar un contenedor colgado."""
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    """Listo para recibir tráfico. Chequeos baratos; cuando haya base de datos, se suma acá."""
    live = sessions.count()
    checks = {
        "templates": (ROOT / "templates").is_dir(),
        "static": (ROOT / "static" / "app.css").is_file(),
        "brand": (BRAND / "logo").is_dir(),
        "sessions": live < sessions.MAX_SESSIONS,
    }
    ok = all(checks.values())
    body = {"status": "ok" if ok else "degraded", "checks": checks, "sessions": live, "demo": demo.enabled()}
    return JSONResponse(body, status_code=200 if ok else 503)


# Rutas que no necesitan sesión: si el latido de la plataforma creara una, cada chequeo ocuparía
# un lugar en el store y terminaría expulsando la sesión de alguien que está usando la app.
STATELESS = ("/static", "/brand", "/health")

CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def session_and_headers(request: Request, call_next):
    stateless = request.url.path.startswith(STATELESS)
    sid, is_new = "", False
    if not stateless:
        sid, sess, is_new = sessions.get(request.cookies.get(sessions.COOKIE))
        request.state.session = sess
        # Traía una cookie de sesión que ya no existe: venció o el servidor se reinició.
        request.state.session_expired = is_new and sessions.COOKIE in request.cookies
    response = await call_next(request)
    if is_new:
        response.set_cookie(sessions.COOKIE, sid, httponly=True, samesite="lax", secure=settings.HTTPS_ONLY_COOKIES or request.url.scheme == "https",
                            max_age=sessions.TTL_SECONDS)
    # Navegación con hx-boost: tras un redirect (POST → 303 → GET) la barra de direcciones debe mostrar
    # la página final. Los cambios de idioma/tema no agregan una entrada al historial.
    q = request.query_params
    if request.headers.get("HX-Boosted"):
        if request.method == "GET" and response.status_code == 200 and "lang" not in q and "theme" not in q:
            response.headers["HX-Push-Url"] = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        elif request.method == "POST":
            # Un envío que vuelve con errores redibuja el mismo paso: la URL no es la del formulario.
            response.headers["HX-Push-Url"] = "false"
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# ─── Datos de resultados ─────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def demo_results():
    """Datos ficticios para mirar la pantalla sin haber buscado (landing en modo demo)."""
    profile, scored = demo.load()
    funnel = {"found": 112, "dups": 6, "excluded": {"modality": 9, "language": 4, "location": 3},
              "out": 50, "evaluated": len(scored), "top_n": 40}
    return profile, scored, funnel


def current_results(request: Request):
    """(perfil, ofertas, embudo) de la búsqueda de esta sesión. Sin búsqueda, los datos de demo."""
    s = sess(request)
    if s.run is not None and s.run.result is not None:
        r = s.run.result
        funnel = {"found": r.total_found, "dups": r.duplicates_removed, "excluded": r.excluded,
                  "out": r.pre_ranked_out, "evaluated": sum(1 for sj in r.scored if sj.evaluated),
                  "top_n": s.run.eval_limit}
        return (s.profile or cand.CandidateProfile()), r.scored, funnel
    return demo_results() if demo.enabled() else None


def results_notice(request: Request) -> str:
    """Si la evaluación se cortó, se dice por qué en vez de mostrar ofertas sin explicación."""
    s, t = sess(request), translator(prefs(request)[0])
    reason = s.run.result.stop_reason if (s.run and s.run.result) else None
    return {"quota": t("wf_quota_stop"), "auth": t("none_evaluated")}.get(reason, "")


def chips(job, t) -> list[str]:
    out = []
    if job.modality in matching.MODALITIES:
        out.append(t(f"mod_{job.modality}"))
    if job.seniority in LEVELS:
        out.append(t(f"sen_{job.seniority}"))
    return out


def filtered(scored, show: str, min_score: int, mods: list[str], lvls: list[str]):
    """Filtros de vista: lo que se elige, se aplica. «No especificado» es una opción más, para que
    lo que no se pudo detectar se pueda ver o esconder a voluntad, sin decidirlo por el usuario."""
    rec = ai_engine.recommended(scored, min_score)
    base = scored if show == "all" else rec
    jobs = [sj for sj in base
            if (not mods or sj.job.modality in mods)
            and (not lvls or sj.job.seniority in lvls)]
    return jobs, rec


def read_filters(request: Request) -> dict:
    q = request.query_params
    s = sess(request)
    default_min = s.run.min_score if s.run is not None else DEFAULT_MIN_SCORE
    try:
        min_score = max(0, min(100, int(q.get("min", default_min))))
    except ValueError:
        min_score = default_min
    try:
        page = max(0, int(q.get("page", 0)))
    except ValueError:
        page = 0
    return {
        "show": "all" if q.get("show") == "all" else "rec",
        "min": min_score,
        "mods": [m for m in q.getlist("mod") if m in matching.MODALITIES or m == normalize.UNKNOWN],
        "lvls": [v for v in q.getlist("lvl") if v in LEVELS or v == normalize.UNKNOWN],
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
    return render(request, "landing.html", n_portals=N_PORTALS, has_results=current_results(request) is not None)


@app.get("/empezar")
def start():
    return RedirectResponse("/asistente", status_code=303)


@app.get("/resultados", response_class=HTMLResponse)
def results(request: Request):
    data = current_results(request)
    if not data:
        return RedirectResponse("/", status_code=303)
    profile, scored, funnel = data
    t = translator(prefs(request)[0])
    meta = " · ".join(x for x in (
        ", ".join(profile.target_roles[:2]),
        t(f"sen_{profile.seniority}") if profile.seniority != cand.UNKNOWN else "",
        profile.location if profile.location != cand.UNKNOWN else "",
    ) if x)
    return render(request, "results.html", meta=meta, funnel=funnel, levels=LEVELS, notice=results_notice(request),
                  modalities=matching.MODALITIES, **list_context(scored, read_filters(request)))


@app.get("/resultados/lista", response_class=HTMLResponse)
def results_list(request: Request):
    """Fragmento HTMX: la lista filtrada (y los contadores, fuera de banda)."""
    data = current_results(request)
    if not data:
        return HTMLResponse("", status_code=204)
    return render(request, "_list.html", **list_context(data[1], read_filters(request)))


@app.post("/carta/{job_id}", response_class=HTMLResponse)
def cover_letter(request: Request, job_id: str):
    """Carta para una oferta concreta, con la clave de esta sesión. Se genera una sola vez."""
    s, t = sess(request), translator(prefs(request)[0])
    data = current_results(request)
    if not data:
        return render(request, "_letter.html", error=t("letter_need_key"))
    profile, scored, _ = data
    sj = next((x for x in scored if dom_id(x.job) == job_id), None)
    if sj is None:
        return HTMLResponse("", status_code=204)
    if not sj.cover_letter:
        if demo.enabled():
            sj.cover_letter = demo.cover_letter(sj.job, prefs(request)[0])
        elif not s.api_key:
            return render(request, "_letter.html", error=t("letter_need_key"))
        else:
            try:
                sj.cover_letter = ai_engine.generate_cover_letter(
                    sj.job, sj.match_reasons, profile.to_prompt(), api_key=s.api_key, model=s.model,
                    signature=profile.full_name)
            except ai_engine.QuotaExceeded:
                return render(request, "_letter.html", error=t("wz_err_quota"))
            except ai_engine.AuthError:
                return render(request, "_letter.html", error=t("wz_err_key"))
            except Exception:
                log.exception("carta job=%s", job_id)
                return render(request, "_letter.html", error=t("letter_error", error=""))
    return render(request, "_letter.html", letter=sj.cover_letter, id=job_id)


@app.get("/resultados/export.json")
def export(request: Request):
    data = current_results(request)
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
