"""
ui.py — Piezas HTML de la interfaz (landing, tarjetas de oferta, anillo de afinidad…).

Funciones puras: reciben el traductor `t(key, **kw)` y devuelven HTML. Todo texto que
venga de afuera (ofertas, empresas, salida de la IA) pasa por html.escape.
Estilos en theme.py; reglas visuales en docs/brand/BRAND.md.
"""

from __future__ import annotations

import html
import zlib
from typing import Callable

T = Callable[..., str]
esc = html.escape

# Colores de avatar: solo de la paleta (BRAND.md §4).
_AVATAR_COLORS = ["#1F6F54", "#A8472E", "#13261E", "#2B5C8A", "#185A44"]


def avatar_color(company: str) -> str:
    return _AVATAR_COLORS[zlib.crc32((company or "?").strip().lower().encode()) % len(_AVATAR_COLORS)]


def affinity(score: int, evaluated: bool = True) -> tuple[str, str]:
    """(clave de etiqueta, color del anillo) según las bandas de docs/scoring.md."""
    if not evaluated:
        return "not_evaluated", "var(--border-2)"
    if score >= 80:
        return "aff_high", "var(--primary)"
    if score >= 60:
        return "aff_good", "var(--score-mid)"
    if score >= 40:
        return "aff_partial", "var(--muted)"
    return "aff_low", "var(--muted)"


def ring_html(score: int, t: T, evaluated: bool = True) -> str:
    key, color = affinity(score, evaluated)
    pct = max(0, min(100, score)) if evaluated else 0
    value = str(score) if evaluated else "—"
    label_color = "var(--primary)" if key == "aff_high" else "var(--warn)" if key == "aff_good" else "var(--muted)"
    return (
        f'<div class="jh-score"><div class="jh-ring" style="background:conic-gradient({color} {pct}%, var(--surface-2) 0)">'
        f'<div>{value}</div></div><small style="color:{label_color}">{esc(t(key))}</small></div>'
    )


# ─── Landing ─────────────────────────────────────────────────────────────────
def nav_html(logo_svg: str, t: T) -> str:
    return (
        f'<div class="jh-nav"><div class="jh-logo" aria-label="JobHunter">{logo_svg}</div>'
        f'<nav class="jh-links"><a href="#como-funciona">{esc(t("nav_how"))}</a>'
        f'<a href="#privacidad">{esc(t("nav_privacy"))}</a></nav></div>'
    )


def hero_copy_html(t: T, n_portals: int) -> str:
    return (
        f'<span class="jh-eyebrow">● {esc(t("hero_eyebrow"))}</span>'
        f'<h1 class="jh-h1">{esc(t("hero_h1_a"))} <em>{esc(t("hero_h1_em"))}</em> {esc(t("hero_h1_b"))}</h1>'
        f'<p class="jh-sub">{esc(t("hero_sub", n=n_portals))}</p>'
    )


def proof_html(t: T) -> str:
    return (
        '<div class="jh-proof"><div class="jh-dots"><i>🩺</i><i>👩‍🍳</i><i>⚡</i><i>📚</i><i>💻</i></div>'
        f'<p><b>{esc(t("proof_title"))}</b><br>{esc(t("proof_sub"))}</p></div>'
    )


def mosaic_html(t: T) -> str:
    health = ('<svg width="88" height="88" viewBox="0 0 96 96" fill="none" stroke="#DDF0E6" stroke-width="6" '
              'stroke-linecap="round"><path d="M28 18v22a20 20 0 0 0 40 0V18"/><path d="M48 60v10a12 12 0 0 0 24 0v-6"/>'
              '<circle cx="72" cy="58" r="7"/></svg>')
    waves = ('<svg width="110" height="110" viewBox="0 0 120 120"><circle cx="60" cy="60" r="46" fill="#13261E"/>'
             '<path d="M26 52l11-9 11 9 11-9 11 9 11-9 11 9M26 72l11-9 11 9 11-9 11 9 11-9 11 9" stroke="#7FC8A9" '
             'stroke-width="6" fill="none" stroke-linejoin="round"/></svg>')
    diamond = ('<svg width="110" height="110" viewBox="0 0 120 120"><path d="M60 14l46 46-46 46-46-46z" fill="#FBE9E4"/>'
               '<path d="M60 38l22 22-22 22-22-22z" fill="#A8472E"/></svg>')
    bolt = ('<svg width="88" height="88" viewBox="0 0 96 96" fill="none" stroke="#7FC8A9" stroke-width="6" '
            'stroke-linejoin="round"><path d="M52 10L24 54h22l-4 32 30-46H50z"/></svg>')
    return (
        '<div class="jh-mosaic" aria-hidden="true">'
        f'<div class="jh-tile" style="background:#1F6F54">{health}<span class="lbl">{esc(t("tile_health"))}</span></div>'
        f'<div class="jh-tile" style="background:#7FC8A9">{waves}</div>'
        f'<div class="jh-tile" style="background:#E07A5F">{diamond}</div>'
        f'<div class="jh-tile" style="background:#13261E">{bolt}<span class="lbl">{esc(t("tile_trades"))}</span></div>'
        '</div>'
    )


def band_html(t: T, n_portals: int) -> str:
    stats = [(str(n_portals), t("band_portals")), ("5", t("band_factors")),
             ("12", t("band_professions")), ("ES·EN", t("band_languages"))]
    cells = "".join(f'<div><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>' for n, l in stats)
    return (
        '<section class="jh-band"><div><div class="jh-shapes"><span style="background:#7FC8A9"></span>'
        '<span style="background:#E07A5F;border-radius:50%"></span><span style="background:#1F6F54;border:2px solid #7FC8A9"></span></div>'
        f'<div class="intro">{esc(t("band_intro"))}</div></div>{cells}</section>'
    )


def steps_html(t: T) -> str:
    colors = ["#1F6F54", "#E07A5F", "#13261E"]
    steps = "".join(
        f'<div class="jh-step"><div class="num" style="background:{colors[i]}">{i + 1}</div>'
        f'<h3>{esc(t(f"how{i + 1}_title"))}</h3><p>{esc(t(f"how{i + 1}_desc"))}</p></div>'
        for i in range(3)
    )
    return f'<span class="jh-label" id="como-funciona">{esc(t("how_label"))}</span><section class="jh-steps">{steps}</section>'


def footer_html(t: T) -> str:
    return (f'<footer class="jh-footer" id="privacidad"><span>{esc(t("footer_privacy"))}</span>'
            f'<span>© JobHunter</span></footer>')


# ─── Asistente ───────────────────────────────────────────────────────────────
def stepper_html(step: int, labels: list[str]) -> str:
    cells = []
    for i, label in enumerate(labels, 1):
        cls = "on" if i == step else "done" if i < step else ""
        mark = "✓" if i < step else str(i)
        cells.append(f'<div class="s {cls}"><b>{mark}</b><span>{esc(label)}</span></div>')
    return f'<div class="jh-stepper">{"".join(cells)}</div>'


# ─── Resultados ──────────────────────────────────────────────────────────────
def results_header_html(title: str, meta: str) -> str:
    return f'<h2 class="jh-title">{esc(title)}</h2><p class="jh-meta">{esc(meta)}</p>'


def job_card_html(sj, t: T, chips: list[str]) -> str:
    """Tarjeta de oferta. `sj` es un ai_engine.ScoredJob; `chips` ya vienen traducidos."""
    job = sj.job
    initial = esc((job.company or job.title or "?").strip()[:1].upper())
    meta = " · ".join(esc(p) for p in (job.company, job.location, job.source) if p)
    chips_html = "".join(f"<span>{esc(c)}</span>" for c in chips if c)

    if sj.evaluated:
        ok = "".join(f"✓ {esc(r)}<br>" for r in sj.match_reasons[:3]) or f'<span class="na">{esc(t("no_reasons"))}</span>'
        no = ("".join(f"• {esc(m)}<br>" for m in sj.missing_skills[:3])
              if sj.missing_skills else f'<span class="na">{esc(t("no_missing"))}</span>')
        why = f'<div class="jh-why"><div class="ok">{ok}</div><div class="no">{no}</div></div>'
        summary = f'<p class="jh-summary">{esc(sj.summary)}</p>' if sj.summary else ""
    else:
        why = f'<div class="jh-why"><div class="na">{esc(t("not_evaluated_hint"))}</div></div>'
        summary = ""

    return (
        f'<article class="jh-job"><div class="jh-avatar" style="background:{avatar_color(job.company)}">{initial}</div>'
        f'<div><h3>{esc(job.title)}</h3><div class="meta">{meta}</div><div class="jh-chips">{chips_html}</div>'
        f'{why}{summary}</div>{ring_html(sj.score, t, sj.evaluated)}</article>'
    )
