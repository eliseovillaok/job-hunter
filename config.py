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
SEARCH_KEYWORDS = [
    "backend developer",
    "java spring boot",
    "cloud engineer",
    "backend engineer",
    "devops engineer",
    "software engineer java",
]

ONLY_REMOTE = True
MIN_MATCH_SCORE = 65   # Mínimo score (0–100) para incluir una oferta en el digest

# --- Perfil del candidato (para el AI Engine) ---
CANDIDATE_PROFILE = """
Nombre: Eliseo Martin Villa
Rol buscado: Backend Engineer / Cloud Engineer (solo remoto)

Stack técnico:
- Java, Spring Boot, REST APIs, JWT, SQL (PostgreSQL, MySQL/MariaDB)
- Python, Bash scripting, automatización
- Docker, Cloud Deployment, Linux
- ERP: Odoo (implementación técnica end-to-end)
- Herramientas: Git, Jira, Scrum

Experiencia:
- IT Lead / Backend Developer en SieteIdeas (ago 2025 – presente)
  * Desarrollo backend, migraciones cloud, automatización de workflows
  * Resultados: reducción 60-80% tareas manuales, >99% disponibilidad
- Java Backend Developer en SISP Tandil (mar–ago 2025)
  * REST APIs en entornos de salud pública, optimización SQL
  * Resultados: mejora 20-40% en queries críticas

Educación: Ingeniería en Sistemas – UNICEN (2021–2026)
Certificaciones: IBM DevOps (en curso), Scrum Fundamentals Certified

Idiomas: Español (nativo), Inglés (intermedio)
Ubicación: Tandil, Argentina — disponible 100% remoto
"""
