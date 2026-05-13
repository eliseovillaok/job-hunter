"""
notifier.py — Envía el digest de oportunidades por email en formato HTML
"""

import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT, SMTP_HOST, SMTP_PORT
from ai_engine import ScoredJob

log = logging.getLogger(__name__)


def _score_color(score: int) -> str:
    if score >= 80:
        return "#22c55e"  # verde
    elif score >= 65:
        return "#f59e0b"  # amarillo
    else:
        return "#94a3b8"  # gris


def _score_label(score: int) -> str:
    if score >= 80:
        return "🔥 Excelente match"
    elif score >= 65:
        return "✅ Buen match"
    else:
        return "🔍 Match parcial"


def _build_html(jobs: list[ScoredJob], run_date: str) -> str:
    top_jobs = [j for j in jobs if j.cover_letter]  # Solo los que tienen cover letter

    job_cards = ""
    for sj in top_jobs:
        reasons_html = "".join(f"<li>{r}</li>" for r in sj.match_reasons)
        missing_html = (
            "".join(f"<li>{m}</li>" for m in sj.missing_skills)
            if sj.missing_skills else "<li>Ninguno crítico</li>"
        )
        cover_html = sj.cover_letter.replace("\n", "<br>") if sj.cover_letter else ""

        source_badge = {
            "GetOnBoard": "#6366f1",
            "Torre.co":   "#0ea5e9",
            "LinkedIn":   "#0077b5",
            "Indeed":     "#2557a7",
        }.get(sj.job.source, "#64748b")

        job_cards += f"""
        <div style="background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                    margin-bottom:28px;overflow:hidden;">
          <!-- Header -->
          <div style="padding:20px 24px;border-bottom:1px solid #f1f5f9;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
              <span style="background:{source_badge};color:#fff;font-size:11px;font-weight:600;
                           padding:3px 9px;border-radius:20px;">{sj.job.source}</span>
              <span style="background:{_score_color(sj.score)};color:#fff;font-size:11px;font-weight:700;
                           padding:3px 9px;border-radius:20px;">{sj.score}/100</span>
              <span style="color:{_score_color(sj.score)};font-size:13px;font-weight:600;">
                {_score_label(sj.score)}</span>
            </div>
            <h2 style="margin:0 0 4px;font-size:18px;color:#1e293b;">{sj.job.title}</h2>
            <p style="margin:0;color:#64748b;font-size:14px;">
              🏢 <strong>{sj.job.company}</strong> &nbsp;|&nbsp; 
              🌐 Remoto &nbsp;|&nbsp;
              <a href="{sj.job.url}" style="color:#6366f1;text-decoration:none;">Ver oferta →</a>
            </p>
          </div>

          <!-- Summary -->
          <div style="padding:16px 24px;background:#f8fafc;border-bottom:1px solid #f1f5f9;">
            <p style="margin:0;color:#475569;font-style:italic;font-size:14px;">{sj.summary}</p>
          </div>

          <!-- Match Details -->
          <div style="padding:20px 24px;display:flex;gap:24px;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
              <h4 style="margin:0 0 8px;color:#22c55e;font-size:13px;text-transform:uppercase;
                          letter-spacing:.05em;">✅ Por qué matchea</h4>
              <ul style="margin:0;padding-left:18px;color:#475569;font-size:13px;line-height:1.7;">
                {reasons_html}
              </ul>
            </div>
            <div style="flex:1;min-width:200px;">
              <h4 style="margin:0 0 8px;color:#f59e0b;font-size:13px;text-transform:uppercase;
                          letter-spacing:.05em;">⚠️ Skills faltantes</h4>
              <ul style="margin:0;padding-left:18px;color:#475569;font-size:13px;line-height:1.7;">
                {missing_html}
              </ul>
            </div>
          </div>

          <!-- Cover Letter -->
          <div style="padding:0 24px 24px;">
            <details style="cursor:pointer;">
              <summary style="font-weight:600;color:#6366f1;font-size:14px;padding:10px 0;
                              border-top:1px solid #f1f5f9;list-style:none;">
                📝 Cover Letter generada — click para ver
              </summary>
              <div style="background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;
                          padding:18px;margin-top:12px;font-size:13px;color:#334155;
                          line-height:1.8;white-space:pre-wrap;font-family:Georgia,serif;">
                {cover_html}
              </div>
            </details>
          </div>
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
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,sans-serif;">

  <div style="max-width:700px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:16px;
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
     '<div style="text-align:center;padding:40px;color:#94a3b8;">No se encontraron matches hoy. ¡Mañana puede ser diferente!</div>'}

    <!-- Footer -->
    <div style="text-align:center;padding:16px;color:#94a3b8;font-size:12px;">
      Generado automáticamente por Job Hunter · Eliseo Martin Villa<br>
      Powered by Google Gemini 🤖
    </div>

  </div>
</body>
</html>
"""


def send_digest(jobs: list[ScoredJob]):
    top_jobs = [j for j in jobs if j.cover_letter]
    run_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not top_jobs:
        log.info("Sin matches para notificar hoy.")
        return

    log.info(f"Enviando digest con {len(top_jobs)} ofertas a {EMAIL_RECIPIENT}...")

    html_body = _build_html(jobs, run_date)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 Job Hunt Digest — {len(top_jobs)} matches — {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        log.info(f"✅ Digest enviado exitosamente a {EMAIL_RECIPIENT}")
    except Exception as e:
        log.error(f"❌ Error enviando email: {e}")
        raise
