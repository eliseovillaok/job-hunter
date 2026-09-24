"""
web/main.py — Interfaz web de JobHunter (FastAPI + Jinja2 + HTMX).

Landing, resultados, salud y el middleware que arma cada pedido: quién es (web/auth.py), su sesión
de trabajo (web/session.py), el token CSRF (web/csrf.py) y las cabeceras de seguridad.
El asistente está en web/wizard.py; la cuenta y el historial, en web/account.py.

Local:  uvicorn web.main:app --reload --port 8600
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import lru_cache

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

import ai_engine
import candidate as cand
import demo
import matching
import normalize
from web import account, auth, csrf, persist, portals, settings, wizard
from web import session as sessions
from web.common import BRAND, LEVELS, ROOT, format_date, prefs, render, sess, translator
# Reexportados para los tests y plantillas existentes.
from web.common import affinity, avatar_color, dom_id, safe_url  # noqa: F401

log = logging.getLogger("jobhunter.web")

PAGE_SIZE = 15
DEFAULT_MIN_SCORE = 65
N_PORTALS = len(portals.available())

app = FastAPI(title="JobHunter", docs_url=None, redoc_url=None, openapi_url=None,
              dependencies=[Depends(csrf.guard)])
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/brand", StaticFiles(directory=BRAND / "logo"), name="brand")
app.include_router(wizard.router)
app.include_router(auth.router)
app.include_router(account.router)


@app.exception_handler(csrf.CSRFError)
async def csrf_failed(request: Request, exc: csrf.CSRFError):
    """La página quedó vieja (o el pedido vino de otro sitio): se pide recargar, no se hace nada."""
    return render(request, "auth.html", status_code=403, mode="csrf", next="/")

# ─── Salud (la plataforma de despliegue consulta estas dos) ──────────────────
@app.get("/health/live", include_in_schema=False)
def health_live():
    """El proceso responde. No toca dependencias: sirve para reiniciar un contenedor colgado."""
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    """Listo para recibir tráfico. Chequeos baratos; la base se consulta con caché de unos segundos."""
    live = sessions.count()
    store = persist.get()
    checks = {
        "templates": (ROOT / "templates").is_dir(),
        "static": (ROOT / "static" / "app.css").is_file(),
        "brand": (BRAND / "logo").is_dir(),
        "sessions": live < sessions.MAX_SESSIONS,
        "database": store is not None and store.ping(),
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


# Lo único que se ve sin cuenta: la landing y las pantallas para crearla o entrar.
PUBLIC = ("/", "/ingresar", "/crear-cuenta", "/crear-cuenta/reenviar", "/auth/confirmar", "/recuperar", "/salir")


def account_wall(request: Request, state: auth.AuthState, loaded: bool) -> Response | None:
    """Sin cuenta no hay asistente ni resultados: se pide entrar y después se vuelve a donde iba."""
    if request.url.path in PUBLIC:
        return None
    if state.down or not loaded:
        return render(request, "auth.html", status_code=503, mode="down", next=request.url.path)
    if state.user is not None:
        return None
    dest = auth.login_url(request.url.path if request.method == "GET" else "/asistente")
    if state.clear:
        dest += "&vencida=1"
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": dest})
    return RedirectResponse(dest, status_code=303)


@app.middleware("http")
async def session_and_headers(request: Request, call_next):
    stateless = request.url.path.startswith(STATELESS)
    sid, is_new, csrf_new, state = "", False, False, None
    secure = settings.HTTPS_ONLY_COOKIES or request.url.scheme == "https"
    if stateless:
        response = await call_next(request)
    else:
        request.state.csrf, csrf_new = csrf.ensure(request)
        state = await run_in_threadpool(auth.resolve, request)
        request.state.user = state.user
        sid, sess, is_new = sessions.get(request.cookies.get(sessions.COOKIE))
        sess, loaded = await auth.bind(request, sid, sess, state.user)
        request.state.session = sess
        # Traía una cookie de sesión que ya no existe: venció o el servidor se reinició.
        request.state.session_expired = is_new and sessions.COOKIE in request.cookies and state.user is not None
        response = account_wall(request, state, loaded) or await call_next(request)
    if state is not None and state.tokens is not None:
        auth.set_cookies(response, state.tokens, request)
    elif state is not None and state.clear:
        auth.clear_cookies(response)
    if csrf_new:
        # La lee app.js para mandarla en cada POST: no puede ser httponly.
        response.set_cookie(csrf.COOKIE, request.state.csrf, samesite="lax", secure=secure, path="/")
    if is_new:
        response.set_cookie(sessions.COOKIE, sid, httponly=True, samesite="lax", secure=secure,
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
    if not stateless:
        # Páginas con datos de la cuenta: que no queden en la caché del navegador ni de un proxy.
        response.headers.setdefault("Cache-Control", "no-store")
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
    """(perfil, ofertas, embudo) que se están mirando: una búsqueda del historial, la de esta sesión
    o, en modo demo y sin ninguna, los datos ficticios."""
    s = sess(request)
    if s.history_view is not None:
        hv = s.history_view
        return (s.profile or cand.CandidateProfile()), hv.scored, hv.funnel
    if s.run is not None and s.run.result is not None:
        return (s.profile or cand.CandidateProfile()), s.run.result.scored, s.run.funnel
    return demo_results() if demo.enabled() else None


def current_run_id(request: Request) -> str | None:
    """search_runs.id de lo que se está mirando (para atar una oferta guardada a su búsqueda)."""
    s = sess(request)
    if s.history_view is not None:
        return s.history_view.run_id
    return (s.run.db_id or None) if s.run is not None else None


def results_notice(request: Request) -> str:
    """Si la evaluación se cortó o el correo no salió, se dice acá en vez de dejarlo en silencio."""
    s, t = sess(request), translator(prefs(request)[0])
    if s.history_view is not None:
        return t("hist_viewing", date=format_date(t, s.history_view.started_at))
    if s.run is None or s.run.result is None:
        return ""
    avisos = []
    stop = {"quota": t("wf_quota_stop"), "auth": t("none_evaluated")}.get(s.run.result.stop_reason)
    if stop:
        avisos.append(stop)
    mail = {"sent": t("mail_sent", to=s.email_recipient), "empty": t("mail_none"),
            "auth": t("mail_err_auth"), "smtp": t("mail_err_smtp")}.get(s.run.email)
    if mail:
        avisos.append(mail)
    return " ".join(avisos)


def chips(job, t) -> list[str]:
    out = []
    if job.modality in matching.MODALITIES:
        out.append(t(f"mod_{job.modality}"))
    if job.seniority in LEVELS:
        out.append(t(f"sen_{job.seniority}"))
    return out


def filtered(scored, show: str, min_score: int, mods: list[str], lvls: list[str], dismissed: set[str] = frozenset()):
    """Filtros de vista: lo que se elige, se aplica. «No especificado» es una opción más, para que
    lo que no se pudo detectar se pueda ver o esconder a voluntad, sin decidirlo por el usuario.
    Las ofertas descartadas solo aparecen en su propia vista, para poder recuperarlas."""
    kept = [sj for sj in scored if persist.job_key(sj.job) not in dismissed]
    rec = ai_engine.recommended(kept, min_score)
    if show == "dismissed":
        base = [sj for sj in scored if persist.job_key(sj.job) in dismissed]
    else:
        base = kept if show == "all" else rec
    jobs = [sj for sj in base
            if (not mods or sj.job.modality in mods)
            and (not lvls or sj.job.seniority in lvls)]
    return jobs, rec


def job_states(request: Request) -> dict[str, str]:
    """Qué ofertas guardó o descartó esta cuenta (clave → estado)."""
    store, user = persist.get(), auth.current_user(request)
    if store is None or user is None:
        return {}
    try:
        return store.job_states(user)
    except persist.StoreError:
        log.warning("resultados: no se pudieron leer las ofertas guardadas", exc_info=True)
        return {}


def read_filters(request: Request) -> dict:
    q = request.query_params
    s = sess(request)
    if s.history_view is not None:
        default_min = s.history_view.min_score
    else:
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
        "show": q.get("show") if q.get("show") in ("all", "dismissed") else "rec",
        "min": min_score,
        "mods": [m for m in q.getlist("mod") if m in matching.MODALITIES or m == normalize.UNKNOWN],
        "lvls": [v for v in q.getlist("lvl") if v in LEVELS or v == normalize.UNKNOWN],
        "page": page,
    }


def card_context(states: dict[str, str]) -> dict:
    """Lo que necesita _job.html además de la oferta."""
    return {"chips": chips, "factors": matching.FACTORS, "weights": matching.WEIGHTS,
            "states": states, "job_key": persist.job_key}


def list_context(scored, f: dict, states: dict[str, str] | None = None) -> dict:
    states = states or {}
    dismissed = {k for k, v in states.items() if v == "dismissed"}
    jobs, rec = filtered(scored, f["show"], f["min"], f["mods"], f["lvls"], dismissed)
    pages = max(1, -(-len(jobs) // PAGE_SIZE))
    page = min(f["page"], pages - 1)
    n_dismissed = sum(1 for sj in scored if persist.job_key(sj.job) in dismissed)
    return {
        "jobs": jobs[page * PAGE_SIZE:(page + 1) * PAGE_SIZE], "n_rec": len(rec), "n_all": len(scored) - n_dismissed,
        "n_dismissed": n_dismissed,
        "any_evaluated": any(sj.evaluated for sj in scored), "page": page, "pages": pages, "f": f,
        **card_context(states),
    }


# ─── Rutas ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    notice = translator(prefs(request)[0])("acc_deleted") if request.query_params.get("cuenta") == "borrada" else None
    return render(request, "landing.html", n_portals=N_PORTALS, has_results=current_results(request) is not None,
                  notice=notice)


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
                  modalities=matching.MODALITIES, **list_context(scored, read_filters(request), job_states(request)))


@app.get("/resultados/lista", response_class=HTMLResponse)
def results_list(request: Request):
    """Fragmento HTMX: la lista filtrada (y los contadores, fuera de banda)."""
    data = current_results(request)
    if not data:
        return HTMLResponse("", status_code=204)
    return render(request, "_list.html", **list_context(data[1], read_filters(request), job_states(request)))


JOB_ACTIONS = {"guardar": "saved", "descartar": "dismissed", "quitar": None}


@app.post("/ofertas/{job_id}/{action}", response_class=HTMLResponse)
def job_action(request: Request, job_id: str, action: str):
    """Guardar, descartar o volver atrás. Responde la tarjeta redibujada (o su aviso de descartada)."""
    if action not in JOB_ACTIONS:
        return HTMLResponse("", status_code=404)
    data = current_results(request)
    sj = next((x for x in data[1] if dom_id(x.job) == job_id), None) if data else None
    store, user = persist.get(), auth.current_user(request)
    if sj is None or store is None or user is None:
        return HTMLResponse("", status_code=204)
    state = JOB_ACTIONS[action]
    try:
        store.set_job_state(user, persist.job_key(sj.job), state, persist.scored_to_dict(sj), current_run_id(request))
    except persist.StoreError:
        t = translator(prefs(request)[0])
        return HTMLResponse(f'<p class="note-inline" role="alert">{t("err_store")}</p>', status_code=503,
                            headers={"HX-Retarget": f"#letter-{job_id}", "HX-Reswap": "innerHTML"})
    states = job_states(request)
    if state == "dismissed":
        r = render(request, "_job_dismissed.html", sj=sj)
    else:
        r = render(request, "_job.html", sj=sj, **card_context(states))
    r.headers["HX-Trigger"] = "jh-jobs"
    return r


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
