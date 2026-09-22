"""web/common.py — Piezas compartidas por las rutas: plantillas, idioma/tema, marca y sesión."""

from __future__ import annotations

import json
import zlib
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from i18n import TRANSLATIONS
from web import session as sessions

ROOT = Path(__file__).resolve().parent
BRAND = ROOT.parent / "docs" / "brand"

LANGS = ("es", "en")
THEMES = ("light", "dark")
LEVELS = ("intern", "junior", "mid", "senior", "lead")

# Todo lo externo (CV, ofertas, salida del LLM) se escapa: Jinja2Templates autoescapa los .html.
templates = Jinja2Templates(directory=ROOT / "templates")


# ─── Marca ───────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def css_tokens() -> str:
    """Variables CSS desde docs/brand/tokens.json (única fuente de colores, BRAND.md §4)."""
    tk = json.loads((BRAND / "tokens.json").read_text(encoding="utf-8"))

    def block(t: dict) -> str:
        return "".join(f"--{k}:{v};" for k, v in t.items())

    light, dark = block(tk["light"]), block(tk["dark"])
    return (f":root{{{light}--forest:{tk['light']['text']};}}"
            f"@media (prefers-color-scheme: dark){{:root:not([data-theme=\"light\"]){{{dark}--forest:#16241E;}}}}"
            f":root[data-theme=\"dark\"]{{{dark}--forest:#16241E;}}")


@lru_cache(maxsize=None)
def logo_svg(name: str) -> str:
    return (BRAND / "logo" / f"{name}.svg").read_text(encoding="utf-8").strip()


_AVATAR_COLORS = ["#1F6F54", "#A8472E", "#13261E", "#2B5C8A", "#185A44"]


def avatar_color(company: str) -> str:
    return _AVATAR_COLORS[zlib.crc32((company or "?").strip().lower().encode()) % len(_AVATAR_COLORS)]


def affinity(score: int, evaluated: bool = True) -> tuple[str, str]:
    """(clave de etiqueta, clase de color) según las bandas de docs/scoring.md."""
    if not evaluated:
        return "not_evaluated", "na"
    if score >= 80:
        return "aff_high", "high"
    if score >= 60:
        return "aff_good", "mid"
    if score >= 40:
        return "aff_partial", "low"
    return "aff_low", "low"


def dom_id(job) -> str:
    """id HTML estable y seguro para una oferta (los ids de los portales traen cualquier carácter)."""
    return f"j{zlib.crc32(f'{job.id}|{job.title}|{job.company}'.encode()):08x}"


def safe_url(url: str | None) -> str | None:
    """Solo enlaces http(s): una oferta no puede inyectar javascript: ni data: en un href."""
    if url and urlparse(url).scheme in ("http", "https"):
        return url
    return None


# ─── Idioma y tema (cookies; ?lang= y ?theme= los cambian) ──────────────────
def prefs(request: Request) -> tuple[str, str | None]:
    lang = request.query_params.get("lang") or request.cookies.get("lang") or "es"
    theme = request.query_params.get("theme") or request.cookies.get("theme")
    return (lang if lang in LANGS else "es"), (theme if theme in THEMES else None)


def translator(lang: str):
    table = TRANSLATIONS[lang]

    def t(key: str, **kw) -> str:
        text = table.get(key) or TRANSLATIONS["es"].get(key, key)
        return text.format(**kw) if kw else text

    return t


def t_for(request: Request):
    return translator(prefs(request)[0])


def sess(request: Request) -> sessions.Session:
    """Sesión del usuario (la crea el middleware de main.py)."""
    return request.state.session


def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    lang, theme = prefs(request)
    response = templates.TemplateResponse(request, name, {
        "t": translator(lang), "lang": lang, "theme": theme, "css_tokens": css_tokens(),
        "logo_light": logo_svg("lockup-light"), "logo_dark": logo_svg("lockup-dark"),
        "avatar_color": avatar_color, "affinity": affinity, "safe_url": safe_url, "dom_id": dom_id, **ctx,
    }, status_code=status_code)
    for key, value in (("lang", request.query_params.get("lang")), ("theme", request.query_params.get("theme"))):
        if value in (LANGS if key == "lang" else THEMES):
            response.set_cookie(key, value, max_age=31536000, samesite="lax")
    return response
