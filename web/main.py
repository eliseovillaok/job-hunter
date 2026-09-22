"""
web/main.py — Interfaz web de JobHunter (FastAPI + Jinja2 + HTMX).

Reemplaza de a poco a la UI de Streamlit (app.py), que sigue desplegada hasta tener paridad.
Etapa 1: landing y resultados con los datos ficticios de demo.py (JOB_HUNTER_DEMO=1).

Local:  uvicorn web.main:app --reload --port 8600
"""

from __future__ import annotations

import json
import zlib
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ai_engine
import candidate as cand
import demo
import matching
import normalize
from i18n import TRANSLATIONS

ROOT = Path(__file__).resolve().parent
BRAND = ROOT.parent / "docs" / "brand"

LANGS = ("es", "en")
THEMES = ("light", "dark")
LEVELS = ("intern", "junior", "mid", "senior", "lead")
PAGE_SIZE = 15
DEFAULT_MIN_SCORE = 65
# TODO(etapa 3): contar desde el registro real de portales (hoy vive en los _defaults de app.py).
N_PORTALS = 19

app = FastAPI(title="JobHunter", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/brand", StaticFiles(directory=BRAND / "logo"), name="brand")
templates = Jinja2Templates(directory=ROOT / "templates")

# Todo lo externo (ofertas, salida del LLM) se escapa: Jinja2Templates autoescapa los .html.
CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


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


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    lang, theme = prefs(request)
    response = templates.TemplateResponse(request, name, {
        "t": translator(lang), "lang": lang, "theme": theme, "css_tokens": css_tokens(),
        "logo_light": logo_svg("lockup-light"), "logo_dark": logo_svg("lockup-dark"),
        "avatar_color": avatar_color, "affinity": affinity, "safe_url": safe_url, "dom_id": dom_id, **ctx,
    })
    for key, value in (("lang", request.query_params.get("lang")), ("theme", request.query_params.get("theme"))):
        if value in (LANGS if key == "lang" else THEMES):
            response.set_cookie(key, value, max_age=31536000, samesite="lax")
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
def start(request: Request):
    # Etapa 2: acá va el asistente. Mientras tanto, en demo lleva directo a los resultados.
    if current_results():
        return RedirectResponse("/resultados", status_code=303)
    return render(request, "landing.html", n_portals=N_PORTALS, has_results=False, wizard_pending=True)


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
