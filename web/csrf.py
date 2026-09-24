"""
web/csrf.py — Toda acción que cambia algo exige un token CSRF (spec §7.3).

Doble envío: el token vive en una cookie propia del sitio y cada POST lo repite en la cabecera
`X-CSRF-Token` (HTMX y los fetch de app.js) o en el campo `csrf_token` (formularios sin JavaScript).
Otro sitio puede hacer que el navegador mande la cookie, pero no puede leerla para repetirla.
SameSite=Lax ayuda, pero no alcanza por sí solo.
"""

from __future__ import annotations

import secrets

from fastapi import Request

COOKIE = "jh_csrf"
HEADER = "X-CSRF-Token"
FIELD = "csrf_token"
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class CSRFError(Exception):
    """El POST no trae el token de este navegador."""


def ensure(request: Request) -> tuple[str, bool]:
    """(token, es_nuevo). Un token ausente o con otra forma se reemplaza."""
    token = request.cookies.get(COOKIE, "")
    if len(token) == 43 and token.replace("-", "").replace("_", "").isalnum():
        return token, False
    return secrets.token_urlsafe(32), True


async def guard(request: Request) -> None:
    """Dependencia global de la app: corre antes de cada ruta."""
    if request.method in SAFE_METHODS:
        return
    expected = request.cookies.get(COOKIE, "")
    sent = request.headers.get(HEADER, "")
    if not sent and request.headers.get("content-type", "").startswith(
            ("application/x-www-form-urlencoded", "multipart/form-data")):
        sent = str((await request.form()).get(FIELD, ""))
    if not expected or not sent or not secrets.compare_digest(expected, sent):
        raise CSRFError
