"""
notifier.py — Resumen de oportunidades por correo, en HTML.

El correo se arma con tablas y estilos en línea porque los clientes de correo ignoran hojas de estilo
y CSS moderno. Colores y bandas salen de docs/brand/tokens.json y de docs/scoring.md (BRAND.md §4 y §6);
el logo viaja adjunto porque no hay dónde alojarlo todavía.

Todo lo que viene de una oferta o del LLM se escapa con html.escape antes de entrar al HTML.
"""

from __future__ import annotations

import html
import json
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import matching
import normalize
from ai_engine import ScoredJob, recommended
from config import SMTP_HOST, SMTP_PORT
from i18n import TRANSLATIONS

# Los clientes de correo no cargan fuentes remotas de forma confiable (Gmail las ignora):
# se piden igual para los que sí pueden y se declara el respaldo del sistema.
BODY_FONT = "'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
DISPLAY_FONT = "'Bricolage Grotesque'," + BODY_FONT
FONTS_URL = "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Inter:wght@400;600;700&display=swap"

log = logging.getLogger(__name__)

SMTP_TIMEOUT = 30          # sin esto, un servidor que no responde deja la búsqueda colgada
LOGO = Path(__file__).resolve().parent / "docs" / "brand" / "logo" / "icon-512.png"
TOKENS = Path(__file__).resolve().parent / "docs" / "brand" / "tokens.json"


class EmailError(Exception):
    """El envío falló por algo que el usuario puede corregir (credenciales, servidor)."""


def _t(lang: str):
    table = TRANSLATIONS.get(lang, TRANSLATIONS["es"])

    def translate(key: str, **kw) -> str:
        text = table.get(key) or TRANSLATIONS["es"].get(key, key)
        return text.format(**kw) if kw else text

    return translate


def _colors() -> dict:
    return json.loads(TOKENS.read_text(encoding="utf-8"))["light"]


def _band(score: int, c: dict) -> tuple[str, str]:
    """(color, clave de etiqueta) según las bandas de docs/scoring.md."""
    if score >= 80:
        return c["primary"], "aff_high"
    if score >= 60:
        return "#C98A1A", "aff_good"
    if score >= 40:
        return c["text-muted"], "aff_partial"
    return c["text-muted"], "aff_low"


def _chips(job, t, c: dict) -> str:
    """Las mismas etiquetas que la tarjeta de la app: modalidad y nivel detectados."""
    labels = []
    if job.modality in matching.MODALITIES:
        labels.append(t(f"mod_{job.modality}"))
    if job.seniority in normalize.SENIORITY_ORDER:
        labels.append(t(f"sen_{job.seniority}"))
    return "".join(
        f'<span style="display:inline-block;font-size:12px;font-weight:600;padding:4px 10px;border-radius:999px;'
        f'background:{c["surface-subtle"]};color:{c["text-2"]};margin:0 6px 6px 0;">{html.escape(x)}</span>'
        for x in labels)


def _card(sj: ScoredJob, t, c: dict) -> str:
    esc = html.escape
    color, label = _band(sj.score, c)
    initial = esc((sj.job.company or sj.job.title or "?").strip()[:1].upper())
    meta = " · ".join(esc(x) for x in (sj.job.company, sj.job.location, sj.job.source) if x)
    reasons = "".join(
        f'<div style="color:{c["success"]};padding:2px 0;">✓ {esc(r)}</div>' for r in sj.match_reasons[:3])
    missing = "".join(
        f'<div style="color:{c["warning"]};padding:2px 0;">• {esc(m)}</div>' for m in sj.missing_skills[:3])
    url = sj.job.url if (sj.job.url or "").startswith(("http://", "https://")) else ""
    button = (f'<a href="{esc(url)}" style="display:inline-block;background:{c["primary"]};color:{c["on-primary"]};'
              f'text-decoration:none;font-size:13.5px;font-weight:600;padding:10px 18px;border-radius:999px;'
              f'font-family:{BODY_FONT};">{t("btn_view")}</a>') if url else ""

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 14px;">
      <tr><td style="background:{c['surface']};border:1px solid {c['border-subtle']};border-radius:22px;padding:22px 24px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td width="52" style="vertical-align:top;padding-right:16px;">
              <div style="width:52px;height:52px;line-height:52px;text-align:center;border-radius:14px;
                          background:{c['primary']};color:{c['on-primary']};font-size:20px;font-weight:800;
                          font-family:{DISPLAY_FONT};">{initial}</div>
            </td>
            <td style="vertical-align:top;">
              <div style="font-size:19px;font-weight:700;color:{c['text']};line-height:1.3;
                          font-family:{DISPLAY_FONT};letter-spacing:-.01em;">{esc(sj.job.title)}</div>
              <div style="font-size:13.5px;color:{c['text-2']};padding:4px 0 10px;">{meta}</div>
              <div>{_chips(sj.job, t, c)}</div>
              <div style="font-size:13.5px;line-height:1.55;padding-top:6px;">{reasons}{missing}</div>
              <div style="padding-top:16px;">{button}</div>
            </td>
            <td width="96" style="vertical-align:top;text-align:center;padding-left:12px;">
              <div style="width:66px;height:66px;line-height:62px;margin:0 auto;border:3px solid {color};
                          border-radius:50%;font-size:22px;font-weight:800;color:{c['text']};
                          font-family:{DISPLAY_FONT};">{sj.score}</div>
              <div style="font-size:11.5px;font-weight:600;color:{color};padding-top:6px;">{t(label)}</div>
            </td>
          </tr>
        </table>
      </td></tr>
    </table>"""


def build_html(jobs: list[ScoredJob], top: list[ScoredJob], *, lang: str, min_score: int, logo_cid: str) -> str:
    t, c = _t(lang), _colors()
    date = datetime.now().strftime("%d/%m/%Y")
    cards = "".join(_card(sj, t, c) for sj in top)
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{t('mail_subject', n=len(top))}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS_URL}" rel="stylesheet">
<style>
  @import url('{FONTS_URL}');
  body, td, div, a, span {{ font-family: {BODY_FONT}; }}
  a {{ color: {c['primary']}; }}
  @media (max-width: 620px) {{
    .card-pad {{ padding: 18px 16px !important; }}
  }}
</style></head>
<body style="margin:0;padding:0;background:{c['bg']};font-family:{BODY_FONT};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{c['bg']};padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <tr><td style="background:{c['surface']};border:1px solid {c['border-subtle']};border-radius:28px 28px 0 0;
                       padding:20px 24px;border-bottom:0;">
          <img src="cid:{logo_cid}" width="36" height="36" alt=""
               style="vertical-align:middle;border-radius:10px;">
          <span style="vertical-align:middle;padding-left:10px;font-size:20px;font-weight:800;color:{c['text']};
                       letter-spacing:-.01em;font-family:{DISPLAY_FONT};">JobHunter</span>
        </td></tr>

        <tr><td style="background:{c['surface']};border:1px solid {c['border-subtle']};border-top:0;border-bottom:0;
                       padding:4px 24px 22px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
                      color:{c['text-muted']};padding-bottom:6px;">{date}</div>
          <div style="font-size:28px;font-weight:800;color:{c['text']};line-height:1.15;letter-spacing:-.02em;
                      font-family:{DISPLAY_FONT};">{t('mail_title', n=len(top))}</div>
          <div style="font-size:14px;color:{c['text-2']};padding-top:8px;line-height:1.6;">
            {t('mail_intro', n=len(top), total=len(jobs), score=min_score)}
          </div>
        </td></tr>

        <tr><td style="background:{c['surface-subtle']};border:1px solid {c['border-subtle']};border-top:0;
                       border-radius:0 0 28px 28px;padding:22px 20px 8px;">
          {cards}
        </td></tr>

        <tr><td style="padding:20px 24px;font-size:12px;color:{c['text-muted']};line-height:1.7;text-align:center;">
          {t('mail_footer')}
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


def send_digest(jobs: list[ScoredJob], *, sender: str, password: str, recipient: str, min_score: int,
                lang: str = "es") -> bool:
    """Envía el resumen con las ofertas recomendadas. False = no había nada que enviar."""
    top = recommended(jobs, min_score)
    if not top:
        log.info("Sin ofertas recomendadas para enviar.")
        return False

    t = _t(lang)
    msg = EmailMessage()
    msg["Subject"] = t("mail_subject", n=len(top))
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(t("mail_plain", n=len(top)))

    logo_cid = make_msgid()[1:-1]
    msg.add_alternative(build_html(jobs, top, lang=lang, min_score=min_score, logo_cid=logo_cid), subtype="html")
    if LOGO.exists():
        msg.get_payload()[1].add_related(LOGO.read_bytes(), maintype="image", subtype="png", cid=f"<{logo_cid}>")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise EmailError("auth") from e
    except (smtplib.SMTPException, OSError) as e:
        raise EmailError("smtp") from e
    log.info("Resumen enviado a %s con %d ofertas.", recipient, len(top))
    return True
