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
| `JH_MAX_RUNS`       | `3`         | Búsquedas corriendo a la vez en el proceso (el resto espera)      |
| `JH_RUN_TIMEOUT`    | `1200`      | Segundos máximos de una búsqueda entera                           |
| `JH_SCRAPE_TIMEOUT` | `480`       | Segundos para leer portales; al agotarse se evalúa lo que hay     |
| `JH_SCRAPE_WORKERS` | `6`         | Portales que se leen en paralelo                                   |
| `GEMINI_RPM`        | `15`        | Llamadas por minuto a Gemini (subir solo con una key paga)        |
| `SUPABASE_URL`      | (vacío)     | URL del proyecto de Supabase (cuentas y datos)                    |
| `SUPABASE_PUBLISHABLE_KEY` | (vacío) | Clave publicable (o `anon` legacy): pedidos con el JWT del usuario |
| `SUPABASE_SECRET_KEY` | (vacío)   | Clave secreta (o `service_role` legacy). Solo servidor, nunca al navegador |
| `JH_AUTH_DAYS`      | `30`        | Días que dura el ingreso en un navegador sin volver a poner la contraseña |

Sin `SUPABASE_URL`, con `JOB_HUNTER_DEMO=1` las cuentas viven en memoria (se pierden al reiniciar);
sin las dos cosas, la app no puede registrar a nadie y `/health/ready` lo informa.
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
MAX_RUNS = _int("JH_MAX_RUNS", 3, minimum=1)
RUN_TIMEOUT = _int("JH_RUN_TIMEOUT", 20 * 60, minimum=60)
SCRAPE_TIMEOUT = _int("JH_SCRAPE_TIMEOUT", 8 * 60, minimum=30)
SCRAPE_WORKERS = _int("JH_SCRAPE_WORKERS", 6, minimum=1)
HTTPS_ONLY_COOKIES = os.environ.get("JH_HTTPS") == "1"
AUTH_DAYS = _int("JH_AUTH_DAYS", 30, minimum=1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
