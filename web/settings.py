"""
web/settings.py — Configuración de despliegue, por variables de entorno.

Todo tiene un valor por defecto razonable: la app arranca sin configurar nada. Para cambiar el
comportamiento en un servidor no hace falta tocar código, solo variables de entorno.

| Variable            | Por defecto | Para qué sirve                                                   |
|---------------------|-------------|------------------------------------------------------------------|
| `JOB_HUNTER_DEMO`   | (vacío)     | `1` = datos ficticios y sin IA (demos y pruebas de interfaz)      |
| `JH_SESSION_TTL`    | `10800`     | Segundos de inactividad antes de borrar la sesión (CV y clave)    |
| `JH_MAX_SESSIONS`   | `500`       | Sesiones simultáneas en memoria (tope de consumo del proceso)     |
| `JH_MAX_CV_MB`      | `10`        | Tamaño máximo del CV                                              |
| `JH_HTTPS`          | (vacío)     | `1` detrás de un proxy TLS: marca la cookie de sesión como segura |
| `GEMINI_RPM`        | `15`        | Llamadas por minuto a Gemini (subir solo con una key paga)        |
"""

from __future__ import annotations

import os


def _int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ[name]))
    except (KeyError, ValueError):
        return default


SESSION_TTL_SECONDS = _int("JH_SESSION_TTL", 3 * 60 * 60, minimum=60)
MAX_SESSIONS = _int("JH_MAX_SESSIONS", 500, minimum=10)
MAX_CV_BYTES = _int("JH_MAX_CV_MB", 10, minimum=1) * 1024 * 1024
HTTPS_ONLY_COOKIES = os.environ.get("JH_HTTPS") == "1"
