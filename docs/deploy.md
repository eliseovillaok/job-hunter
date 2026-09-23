# Despliegue

JobHunter se despliega como **un solo proceso**: `uvicorn web.main:app`. No hay base de datos ni
worker todavía, así que alcanza con un servicio web y un dominio.

El repo ya trae lo necesario para cualquiera de las dos plataformas candidatas: `Dockerfile`,
`.dockerignore`, chequeos de salud (`/health/live` y `/health/ready`) y toda la configuración por
variables de entorno. **Todavía no hay que elegir**: el desarrollo sigue en local.

## Probar la imagen en local

```bash
docker build -t jobhunter .
docker run --rm -p 8000:8000 -e JOB_HUNTER_DEMO=1 jobhunter
```

Después, `http://localhost:8000` y `http://localhost:8000/health/ready`.

## Variables de entorno

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `PORT` | `8000` | La inyecta la plataforma; el contenedor la respeta |
| `JH_HTTPS` | (vacío) | `1` en producción: marca la cookie de sesión como `Secure` |
| `JH_SESSION_TTL` | `10800` | Segundos de inactividad antes de borrar la sesión (CV y clave) |
| `JH_MAX_SESSIONS` | `500` | Sesiones simultáneas en memoria |
| `JH_MAX_CV_MB` | `10` | Tamaño máximo del CV |
| `GEMINI_RPM` | `15` | Llamadas por minuto a Gemini |
| `JOB_HUNTER_DEMO` | (vacío) | `1` = datos ficticios, sin IA ni red. **Nunca en producción** |

No hay secretos del servidor todavía: la clave de Gemini la pone cada usuario y vive solo en su
sesión. Cuando existan (Supabase, Stripe, Resend), van en el gestor de secretos de la plataforma,
nunca en el repo.

## Railway o Render

Las dos corren la misma imagen y dan HTTPS y dominio propio sin configurar nada. La spec (§15.4)
pide **elegir una y comprometerse**; llevar dos stacks en paralelo es trabajo de más.

| | Railway | Render |
|---|---|---|
| Entrada | Plan Hobby, USD 5/mes con USD 5 de crédito de uso incluido | Workspace Hobby USD 0/mes + cómputo (la instancia gratuita se duerme) |
| Modelo de cobro | Por consumo real (CPU/RAM/red) contra el crédito | Por instancia, precio fijo según tamaño |
| Despliegue | Detecta el `Dockerfile` y despliega desde GitHub | Igual, con `render.yaml` opcional |
| Salud | Chequeo HTTP configurable | Chequeo HTTP nativo (`/health/ready`) |
| Tareas programadas | No tiene cron propio (lo resuelve QStash, que es el plan de la Fase 5) | Cron jobs nativos |
| Entornos | Un entorno por rama | Servicios separados para staging y producción |
| Cuándo conviene | Un solo servicio chico y tráfico irregular: se paga lo que se usa | Precio previsible y cron incluido |

**Recomendación:** Railway para arrancar —un servicio, tráfico bajo, factura por uso— y Render si
más adelante conviene precio fijo o cron nativo. La automatización va por QStash en las dos, así
que el cron de Render no es un motivo decisivo.

Precios y planes cambian seguido: verificarlos el día que se contrate (spec §31.7).

## Pasos, el día que se elija

1. Crear el servicio desde el repo de GitHub, rama `main`, build por `Dockerfile`.
2. Cargar las variables de entorno de la tabla (con `JH_HTTPS=1`).
3. Apuntar el chequeo de salud a `/health/ready`.
4. Apuntar `jobhunter.site` al servicio y dejar que la plataforma gestione el certificado.
5. Crear un segundo servicio `staging` desde la misma rama, con sus propias variables.
6. Verificar: `/health/live`, `/health/ready`, el flujo completo en staging y recién después producción.

## Streamlit Cloud (retirado)

La app vieja (`app.py`) estuvo publicada en Streamlit Cloud. Ese despliegue se da de baja: el
producto es `web/`. Mientras `app.py` siga en el repo se corre solo en local, con
`pip install -r requirements-dev.txt` (Streamlit ya no es una dependencia de producción).
