# =============================================================================
# JOB HUNTER — CONFIG
# Completá con tus datos antes de correr el script
# =============================================================================

import os

# --- Google Gemini API (gratuito) ---
# Obtené tu key gratis en: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "REEMPLAZAR")

# --- Email (Gmail recomendado) ---
EMAIL_SENDER    = os.getenv("EMAIL_SENDER",   "tu_email@gmail.com")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD", "tu_app_password")   # Gmail App Password
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "tu_email@gmail.com")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# --- Búsqueda ---
# Estos valores son sobreescritos en runtime por el wizard de app.py
SEARCH_KEYWORDS = []

ONLY_REMOTE = True
MIN_MATCH_SCORE = 65   # Mínimo score (0–100) para incluir una oferta en el digest

# --- Perfil del candidato (para el AI Engine) ---
# Sobreescrito en runtime por el wizard de app.py (cfg.CANDIDATE_PROFILE = ...)
CANDIDATE_PROFILE = ""
