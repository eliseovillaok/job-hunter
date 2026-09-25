"""
web/auth.py — Cuentas: alta, ingreso, salida, confirmación del correo y nueva contraseña.

La sesión de la cuenta viaja en dos cookies httponly (spec §7.1): `jh_access` (el JWT de Supabase,
dura una hora) y `jh_refresh` (lo renueva, dura JH_AUTH_DAYS). El navegador nunca ve una clave del
servidor ni guarda nada en localStorage. En cada pedido el middleware (main.py) llama a `resolve`
para saber quién es y a `bind` para que la sesión en memoria sea de esa cuenta.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

import candidate as cand
from web import persist, portals, settings
from web import session as sessions
from web.common import prefs, render, t_for
from web.persist import AuthError, StoreError, Tokens, User

log = logging.getLogger("jobhunter.auth")

ACCESS, REFRESH = "jh_access", "jh_refresh"
MAX_EMAIL = 254
MAX_PASSWORD = 128

router = APIRouter()


# ─── Quién es ────────────────────────────────────────────────────────────────
@dataclass
class AuthState:
    user: Optional[User] = None
    tokens: Optional[Tokens] = None   # se renovó el token: hay que dejar las cookies nuevas
    clear: bool = False               # las cookies ya no sirven
    down: bool = False                # Supabase no respondió: no se sabe


def resolve(request: Request) -> AuthState:
    """Bloqueante (habla con Auth): el middleware lo llama en el pool de hilos."""
    store = persist.get()
    access, refresh = request.cookies.get(ACCESS, ""), request.cookies.get(REFRESH, "")
    if store is None or not (access or refresh):
        return AuthState()
    try:
        user = store.user_for_token(access) if access else None
        if user:
            return AuthState(user)
        if refresh:
            tokens = store.refresh(refresh)
            return AuthState(tokens.user, tokens=tokens)
        return AuthState(clear=True)
    except AuthError as e:
        return AuthState(down=True) if e.code == "unavailable" else AuthState(clear=True)
    except StoreError:
        log.warning("auth: no se pudo validar la sesión", exc_info=True)
        return AuthState(down=True)


def current_user(request: Request) -> Optional[User]:
    return getattr(request.state, "user", None)


def _secure(request: Request) -> bool:
    return settings.HTTPS_ONLY_COOKIES or request.url.scheme == "https"


def set_cookies(response: Response, tokens: Tokens, request: Request) -> None:
    secure = _secure(request)
    response.set_cookie(ACCESS, tokens.access_token, max_age=max(60, tokens.expires_in), httponly=True,
                        secure=secure, samesite="lax", path="/")
    response.set_cookie(REFRESH, tokens.refresh_token, max_age=settings.AUTH_DAYS * 86400, httponly=True,
                        secure=secure, samesite="lax", path="/")


def clear_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS, path="/")
    response.delete_cookie(REFRESH, path="/")


# ─── La sesión en memoria es de una cuenta ───────────────────────────────────
def hydrate(sess: sessions.Session, user: User) -> None:
    """Copia a la sesión lo guardado de la cuenta. Bloqueante: va en el pool de hilos."""
    from web import wizard   # tarde: wizard importa este módulo a través de common/run

    acc = persist.get().account(user)
    sess.plan = acc.plan
    if acc.cv:
        sess.cv = sessions.CVFile(name=acc.cv["name"], mime=acc.cv["mime"], data=b"", id=acc.cv["sha"][:16],
                                  size=int(acc.cv.get("size") or 0))
        sess.cv_doc_id = acc.cv["id"]
        if acc.cv["parsed"]:
            sess.analyzed_cv_id = sess.cv.id
    # Un perfil sacado de un CV que ya se reemplazó (o que todavía no se analizó) no se muestra.
    manual = acc.profile_source == "manual" and not acc.cv
    from_cv = acc.profile_source == "cv" and acc.cv is not None and acc.cv["parsed"]
    if acc.profile is not None and (manual or from_cv):
        sess.profile = cand.CandidateProfile.from_dict(acc.profile)
        sess.profile_confirmed = acc.profile_confirmed
        sess.manual_profile = manual
    p = acc.preferences
    if p:
        available = {x.key for x in portals.available()}
        sess.terms = list(p.get("terms") or [])
        sess.modalities = [m for m in p.get("modalities") or [] if m in ("remote", "hybrid", "onsite")]
        sess.locations = p.get("locations") or ""
        sess.job_languages = [c for c in p.get("job_languages") or [] if c in wizard.JOB_LANGUAGES]
        sess.portals = [k for k in p.get("portals") or [] if k in available] or sess.portals
        sess.min_score = int(p.get("min_score") or sess.min_score)
        sess.eval_limit = int(p.get("eval_limit") or sess.eval_limit)
    elif sess.profile is not None:
        sess.terms = sess.profile.all_search_terms()
        sess.job_languages = wizard.job_lang_codes(sess.profile)
    wizard.fit_to_plan(sess)
    latest = persist.get().latest_run_with_results(user)
    if latest:
        from web.account import history_view
        sess.history_view = history_view(latest)
    sess.user_id = user.id


async def bind(request: Request, sid: str, sess: sessions.Session, user: Optional[User]) -> tuple[sessions.Session, bool]:
    """(sesión de esta cuenta, se pudo cargar). Si entró otra cuenta en el navegador, se empieza de cero."""
    if user is None:
        if sess.user_id:
            sess = sessions.replace(sid, sessions.Session())
        return sess, True
    if sess.user_id == user.id:
        return sess, True
    fresh = sessions.Session()
    try:
        await run_in_threadpool(hydrate, fresh, user)
    except StoreError:
        log.warning("auth: no se pudo cargar la cuenta", exc_info=True)
        return sessions.replace(sid, sessions.Session()), False
    return sessions.replace(sid, fresh), True


# ─── Pantallas ───────────────────────────────────────────────────────────────
def safe_next(value: str | None, default: str = "/asistente") -> str:
    """Solo rutas propias: `next` no puede llevar a otro sitio."""
    v = (value or "").strip()
    if v.startswith("/") and not v.startswith(("//", "/\\")) and "\n" not in v and "\r" not in v:
        return v
    return default


def login_url(path: str) -> str:
    return f"/ingresar?next={quote(safe_next(path), safe='/')}"


def page(request: Request, mode: str, status_code: int = 200, **ctx) -> HTMLResponse:
    return render(request, "auth.html", status_code=status_code, mode=mode,
                  next=safe_next(request.query_params.get("next") or ctx.pop("next", None)), **ctx)


def _error(request: Request, mode: str, e: AuthError, **ctx) -> HTMLResponse:
    status = 429 if e.code == "rate_limited" else 503 if e.code == "unavailable" else 400
    return page(request, mode, status_code=status, error=t_for(request)(f"auth_err_{e.code}"), code=e.code, **ctx)


def _store_or_503(request: Request):
    store = persist.get()
    if store is None:
        return None, page(request, "down", status_code=503)
    return store, None


def _signed_in(request: Request, tokens: Tokens, to: str) -> Response:
    """Entró: sesión en memoria nueva (nada de la anterior) y cookies de la cuenta."""
    sessions.drop(request.cookies.get(sessions.COOKIE))
    response = RedirectResponse(to, status_code=303)
    set_cookies(response, tokens, request)
    # Sin esto, el primer pedido ya adentro traería una cookie de sesión borrada y se leería como vencida.
    response.delete_cookie(sessions.COOKIE, path="/")
    return response


def _clean(email: str, password: str = "") -> tuple[str, str]:
    return email.strip()[:MAX_EMAIL], password[:MAX_PASSWORD]


@router.get("/ingresar", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse(safe_next(request.query_params.get("next")), status_code=303)
    notice = t_for(request)("auth_expired") if request.query_params.get("vencida") else None
    return page(request, "login", notice=notice)


@router.post("/ingresar")
def login(request: Request, email: str = Form(""), password: str = Form(""), next: str = Form("")):
    store, down = _store_or_503(request)
    if down:
        return down
    email, password = _clean(email, password)
    try:
        tokens = store.sign_in(email, password)
    except AuthError as e:
        return _error(request, "login", e, email=email, next=next)
    return _signed_in(request, tokens, safe_next(next))


@router.get("/crear-cuenta", response_class=HTMLResponse)
def signup_page(request: Request):
    if current_user(request):
        return RedirectResponse("/asistente", status_code=303)
    return page(request, "signup")


@router.post("/crear-cuenta")
def signup(request: Request, email: str = Form(""), password: str = Form(""), next: str = Form("")):
    store, down = _store_or_503(request)
    if down:
        return down
    email, password = _clean(email, password)
    try:
        tokens = store.sign_up(email, password, prefs(request)[0])
    except AuthError as e:
        return _error(request, "signup", e, email=email, next=next)
    if tokens is None:
        return page(request, "check_email", email=email)
    return _signed_in(request, tokens, safe_next(next))


@router.post("/crear-cuenta/reenviar", response_class=HTMLResponse)
def resend(request: Request, email: str = Form("")):
    store, down = _store_or_503(request)
    if down:
        return down
    email, _ = _clean(email)
    try:
        store.resend_confirmation(email)
    except AuthError as e:
        return _error(request, "check_email", e, email=email)
    return page(request, "check_email", email=email, resent=True)


@router.get("/auth/confirmar")
def confirm(request: Request, token_hash: str = "", type: str = ""):
    """Enlace del correo (confirmación o nueva contraseña). El token se verifica en el servidor."""
    store, down = _store_or_503(request)
    if down:
        return down
    if type not in ("email", "recovery") or not token_hash or len(token_hash) > 200:
        return page(request, "link_invalid", status_code=400)
    try:
        tokens = store.verify_link(token_hash, type)
    except AuthError as e:
        if e.code == "unavailable":
            return _error(request, "link_invalid", e)
        return page(request, "link_invalid", status_code=400)
    return _signed_in(request, tokens, "/nueva-clave" if type == "recovery" else "/asistente")


@router.get("/recuperar", response_class=HTMLResponse)
def recover_page(request: Request):
    return page(request, "recover")


@router.post("/recuperar", response_class=HTMLResponse)
def recover(request: Request, email: str = Form("")):
    store, down = _store_or_503(request)
    if down:
        return down
    email, _ = _clean(email)
    if "@" not in email:
        return _error(request, "recover", AuthError("invalid_email"), email=email)
    try:
        store.send_password_reset(email)
    except AuthError as e:
        if e.code != "invalid_email":   # un correo inexistente no se distingue de uno válido
            return _error(request, "recover", e, email=email)
    return page(request, "reset_sent", email=email)


@router.get("/nueva-clave", response_class=HTMLResponse)
def new_password_page(request: Request):
    return page(request, "new_password")


@router.post("/nueva-clave")
def new_password(request: Request, password: str = Form("")):
    user = current_user(request)
    _, password = _clean("", password)
    try:
        persist.get().set_password(user, password)
    except AuthError as e:
        return _error(request, "new_password", e)
    return RedirectResponse("/cuenta?clave=1", status_code=303)


@router.post("/salir")
def logout(request: Request):
    user = current_user(request)
    if user is not None and persist.get() is not None:
        persist.get().sign_out(user)
    sessions.drop(request.cookies.get(sessions.COOKIE))
    response = RedirectResponse("/", status_code=303)
    clear_cookies(response)
    response.delete_cookie(sessions.COOKIE, path="/")
    return response
