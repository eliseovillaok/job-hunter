"""
web/account.py — Mi cuenta (uso del plan, CV, exportar y borrar) e historial (búsquedas y guardadas).

El usuario controla sus datos (spec §4.4): ve qué hay guardado, lo descarga en JSON y lo borra de
verdad. Borrar la cuenta se confirma escribiendo el correo, y lo orquesta el store (web/persist.py).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from web import auth, persist, wizard
from web import session as sessions
from web.common import format_date, render, sess, t_for
from web.persist import StoreError
from web.session import HistoryView

log = logging.getLogger("jobhunter.account")
router = APIRouter()

RUN_STATUS = ("running", "succeeded", "partial", "failed", "canceled", "queued")


def history_view(row: dict) -> HistoryView:
    """Una fila de search_runs (con su foto de resultados) lista para /resultados."""
    query = row.get("query") or {}
    return HistoryView(
        run_id=str(row["id"]),
        scored=[persist.scored_from_dict(d) for d in row.get("results") or []],
        funnel=row.get("funnel"),
        min_score=int(query.get("min_score") or 65),
        eval_limit=int(query.get("eval_limit") or 40),
        started_at=row.get("started_at"),
    )


def _store_user(request: Request):
    return persist.get(), auth.current_user(request)


# ─── Mi cuenta ───────────────────────────────────────────────────────────────
@router.get("/cuenta", response_class=HTMLResponse)
def account_page(request: Request):
    return _account(request)


def _account(request: Request, status_code: int = 200, error: str | None = None) -> HTMLResponse:
    s, t = sess(request), t_for(request)
    notice = {"1": t("auth_password_changed"), "cv": t("acc_cv_deleted")}.get(request.query_params.get("clave")
                                                                              or request.query_params.get("hecho") or "")
    return render(request, "account.html", status_code=status_code, s=s, usage=wizard.usage(request),
                  limits=wizard.limits(s), notice=notice, error=error)


@router.post("/cuenta/cv/borrar")
def delete_cv(request: Request):
    store, user = _store_user(request)
    s = sess(request)
    try:
        store.delete_cv(user)
    except StoreError:
        log.warning("cuenta: no se pudo borrar el CV", exc_info=True)
        return _account(request, status_code=503, error=t_for(request)("err_store"))
    s.cv, s.cv_doc_id, s.analyzed_cv_id = None, "", ""
    if not s.manual_profile:
        s.profile, s.profile_confirmed = None, False
    return RedirectResponse("/cuenta?hecho=cv", status_code=303)


@router.get("/cuenta/datos.json")
def export_data(request: Request):
    store, user = _store_user(request)
    try:
        data = store.export(user)
    except StoreError:
        log.warning("cuenta: no se pudo exportar", exc_info=True)
        return _account(request, status_code=503, error=t_for(request)("err_store"))
    body = json.dumps({"exported_at": persist.now_utc().isoformat(), **data}, ensure_ascii=False, indent=2, default=str)
    name = f"jobhunter-datos-{datetime.now().strftime('%Y%m%d')}.json"
    return Response(body, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/cuenta/borrar")
def delete_account(request: Request, confirm: str = Form("")):
    store, user = _store_user(request)
    t = t_for(request)
    if confirm.strip().lower() != user.email.strip().lower():
        return _account(request, status_code=400, error=t("acc_delete_mismatch"))
    s = sess(request)
    if s.run is not None and s.run.active:
        s.run.cancel()
    try:
        store.delete_account(user)
    except (StoreError, persist.AuthError):
        log.warning("cuenta: el borrado no terminó", exc_info=True)
        return _account(request, status_code=503, error=t("acc_delete_failed"))
    sessions.drop(request.cookies.get(sessions.COOKIE))
    response = RedirectResponse("/?cuenta=borrada", status_code=303)
    auth.clear_cookies(response)
    response.delete_cookie(sessions.COOKIE, path="/")
    return response


# ─── Historial ───────────────────────────────────────────────────────────────
@router.get("/historial", response_class=HTMLResponse)
def history(request: Request):
    store, user = _store_user(request)
    t = t_for(request)
    try:
        runs, saved = store.runs(user), store.saved_jobs(user)
    except StoreError:
        log.warning("historial: no se pudo leer", exc_info=True)
        return render(request, "history.html", status_code=503, runs=[], saved=[], error=t("err_store"))
    for r in runs:
        r["status"] = r.get("status") if r.get("status") in RUN_STATUS else "failed"
        r["terms"] = ", ".join(((r.get("query") or {}).get("terms") or [])[:4])
        r["date"] = format_date(t, r.get("started_at"))
    for j in saved:
        j["scored"] = persist.scored_from_dict(j["job"] or {})
    return render(request, "history.html", runs=runs, saved=saved)


@router.get("/historial/{run_id}")
def open_run(request: Request, run_id: str):
    """Abre una búsqueda anterior en la pantalla de resultados."""
    store, user = _store_user(request)
    try:
        row = store.run(user, run_id)
    except StoreError:
        return RedirectResponse("/historial", status_code=303)
    if not row or not row.get("results"):
        return RedirectResponse("/historial", status_code=303)
    sess(request).history_view = history_view(row)
    return RedirectResponse("/resultados", status_code=303)


@router.post("/guardadas/{key}/quitar", response_class=HTMLResponse)
def unsave(request: Request, key: str):
    store, user = _store_user(request)
    if not (len(key) == 32 and all(c in "0123456789abcdef" for c in key)):
        return HTMLResponse("", status_code=404)
    try:
        store.set_job_state(user, key, None, {}, None)
    except StoreError:
        return HTMLResponse(f'<p class="field-err" role="alert">{t_for(request)("err_store")}</p>', status_code=503)
    if request.headers.get("HX-Request"):
        return HTMLResponse("")
    return RedirectResponse("/historial", status_code=303)
