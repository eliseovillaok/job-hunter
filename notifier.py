"""
notifier.py — Envía el digest de oportunidades por email en formato HTML
"""

import html
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import SMTP_HOST, SMTP_PORT
from ai_engine import ScoredJob, recommended

log = logging.getLogger(__name__)


def _score_color(score: int) -> str:
    if score >= 80:
        return "#377227"  # verde
    elif score >= 65:
        return "#8F5D00"  # amarillo
    else:
        return "#58736A"  # gris


def _score_label(score: int) -> str:
    if score >= 80:
        return "🔥 Excelente match"
    elif score >= 65:
        return "✅ Buen match"
    else:
        return "🔍 Match parcial"


def _build_html(jobs: list[ScoredJob], top_jobs: list[ScoredJob], run_date: str) -> str:
    esc = html.escape  # todo el contenido viene de ofertas externas o del LLM

    job_cards = ""
    for sj in top_jobs:
        reasons_html = "".join(f"<li>{esc(r)}</li>" for r in sj.match_reasons)
        missing_html = (
            "".join(f"<li>{esc(m)}</li>" for m in sj.missing_skills)
            if sj.missing_skills else "<li>Ninguno crítico</li>"
        )
        cover_section = ""
        if sj.cover_letter:
            cover_section = f"""
          <div style="padding:0 24px 24px;">
            <details style="cursor:pointer;">
              <summary style="font-weight:600;color:#1F6F54;font-size:14px;padding:10px 0;
                              border-top:1px solid #F4F8F5;list-style:none;">
                📝 Cover Letter generada — click para ver
              </summary>
              <div style="background:#FFFFFF;border:1px solid #DCE8E1;border-radius:8px;
                          padding:18px;margin-top:12px;font-size:13px;color:#13261E;
                          line-height:1.8;white-space:pre-wrap;font-family:Georgia,serif;">
                {esc(sj.cover_letter)}
              </div>
            </details>
          </div>"""
        modality = "🌐 Remoto" if sj.job.remote else f"📍 {esc(sj.job.location or 'Ubicación no especificada')}"

        source_badge = {
            "GetOnBoard": "#1F6F54",
            "Torre.co":   "#2B5C8A",
            "LinkedIn":   "#2B5C8A",
            "Indeed":     "#2B5C8A",
        }.get(sj.job.source, "#3E5A4E")

        job_cards += f"""
        <div style="background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                    margin-bottom:28px;overflow:hidden;">
          <!-- Header -->
          <div style="padding:20px 24px;border-bottom:1px solid #F4F8F5;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
              <span style="background:{source_badge};color:#fff;font-size:11px;font-weight:600;
                           padding:3px 9px;border-radius:20px;">{esc(sj.job.source)}</span>
              <span style="background:{_score_color(sj.score)};color:#fff;font-size:11px;font-weight:700;
                           padding:3px 9px;border-radius:20px;">{sj.score}/100</span>
              <span style="color:{_score_color(sj.score)};font-size:13px;font-weight:600;">
                {_score_label(sj.score)}</span>
            </div>
            <h2 style="margin:0 0 4px;font-size:18px;color:#13261E;">{esc(sj.job.title)}</h2>
            <p style="margin:0;color:#3E5A4E;font-size:14px;">
              🏢 <strong>{esc(sj.job.company)}</strong> &nbsp;|&nbsp; 
              {modality} &nbsp;|&nbsp;
              <a href="{esc(sj.job.url, quote=True)}" style="color:#1F6F54;text-decoration:none;">Ver oferta →</a>
            </p>
          </div>

          <!-- Summary -->
          <div style="padding:16px 24px;background:#EAF3EE;border-bottom:1px solid #F4F8F5;">
            <p style="margin:0;color:#3E5A4E;font-style:italic;font-size:14px;">{esc(sj.summary)}</p>
          </div>

          <!-- Match Details -->
          <div style="padding:20px 24px;display:flex;gap:24px;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
              <h4 style="margin:0 0 8px;color:#377227;font-size:13px;text-transform:uppercase;
                          letter-spacing:.05em;">✅ Por qué matchea</h4>
              <ul style="margin:0;padding-left:18px;color:#3E5A4E;font-size:13px;line-height:1.7;">
                {reasons_html}
              </ul>
            </div>
            <div style="flex:1;min-width:200px;">
              <h4 style="margin:0 0 8px;color:#8F5D00;font-size:13px;text-transform:uppercase;
                          letter-spacing:.05em;">⚠️ Skills faltantes</h4>
              <ul style="margin:0;padding-left:18px;color:#3E5A4E;font-size:13px;line-height:1.7;">
                {missing_html}
              </ul>
            </div>
          </div>

          {cover_section}
        </div>
        """

    total = len(jobs)
    matched = len(top_jobs)

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Job Hunt Digest — {run_date}</title>
</head>
<body style="margin:0;padding:0;background:#F4F8F5;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,sans-serif;">

  <div style="max-width:700px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1F6F54,#185A44);border-radius:16px;
                padding:32px;margin-bottom:24px;text-align:center;color:#fff;">
      <h1 style="margin:0 0 8px;font-size:26px;">🎯 Job Hunt Digest</h1>
      <p style="margin:0;opacity:.85;font-size:14px;">{run_date}</p>
      <div style="display:inline-flex;gap:16px;margin-top:16px;flex-wrap:wrap;
                  justify-content:center;">
        <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;">
          <div style="font-size:22px;font-weight:700;">{total}</div>
          <div style="font-size:11px;opacity:.8;">OFERTAS ANALIZADAS</div>
        </div>
        <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:10px 20px;">
          <div style="font-size:22px;font-weight:700;">{matched}</div>
          <div style="font-size:11px;opacity:.8;">MATCHES ENCONTRADOS</div>
        </div>
      </div>
    </div>

    <!-- Job Cards -->
    {job_cards if job_cards else
     '<div style="text-align:center;padding:40px;color:#58736A;">No se encontraron matches hoy. ¡Mañana puede ser diferente!</div>'}

    <!-- Footer -->
    <div style="text-align:center;padding:16px;color:#58736A;font-size:12px;">
      Generado automáticamente por Job Hunter<br>
      Powered by Google Gemini 🤖
    </div>

  </div>
</body>
</html>
"""


def send_digest(jobs: list[ScoredJob], *, sender: str, password: str, recipient: str, min_score: int) -> bool:
    """Envía el digest con las ofertas recomendadas. Devuelve False si no había nada para enviar."""
    top_jobs = recommended(jobs, min_score)
    run_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not top_jobs:
        log.info("Sin matches para notificar hoy.")
        return False

    log.info(f"Enviando digest con {len(top_jobs)} ofertas...")

    html_body = _build_html(jobs, top_jobs, run_date)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 Job Hunt Digest — {len(top_jobs)} matches — {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"] = sender
    msg["To"] = recipient

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
    log.info("✅ Digest enviado")
    return True
