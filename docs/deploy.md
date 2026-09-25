# Despliegue

JobHunter se despliega como **un solo proceso**: `uvicorn web.main:app`, más un proyecto de
**Supabase** (cuentas, Postgres y Storage para los CV). No hay worker todavía: alcanza con un servicio
web, un proyecto de Supabase y un dominio.

Las sesiones de trabajo (el asistente a medio completar, la búsqueda en curso) siguen en la memoria
del proceso y se reconstruyen desde la base al volver a entrar. Por eso, por ahora, **una sola
instancia** del servicio.

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
| `JH_MAX_RUNS` | `3` | Búsquedas corriendo a la vez en el proceso; el resto espera |
| `JH_RUN_TIMEOUT` | `1200` | Segundos máximos de una búsqueda entera |
| `JH_SCRAPE_TIMEOUT` | `480` | Segundos para leer portales; al agotarse se evalúa lo que hay |
| `JH_SCRAPE_WORKERS` | `6` | Portales que se leen en paralelo |
| `GEMINI_RPM` | `15` | Llamadas por minuto a Gemini |
| `GEMINI_EMBED_RPM` | `5` | Llamadas por minuto a los embeddings (cupo propio, más bajo) |
| `JOB_HUNTER_DEMO` | (vacío) | `1` = datos ficticios, sin IA ni red. **Nunca en producción** |
| `SUPABASE_URL` | (vacío) | URL del proyecto (`https://<ref>.supabase.co`) |
| `SUPABASE_PUBLISHABLE_KEY` | (vacío) | Clave publicable (`sb_publishable_…`, o `anon` legacy) |
| `SUPABASE_SECRET_KEY` | (vacío) | Clave secreta (`sb_secret_…`, o `service_role` legacy). **Secreto** |
| `JH_AUTH_DAYS` | `30` | Días que dura el ingreso en un navegador sin volver a poner la contraseña |

Sin las tres `SUPABASE_*` la app no puede registrar a nadie y `/health/ready` informa
`"database": false`; con `JOB_HUNTER_DEMO=1` las cuentas viven en memoria y se pierden al reiniciar.

La clave secreta es el único secreto del servidor por ahora (la de Gemini la pone cada usuario y vive
solo en su sesión): va en el gestor de secretos de la plataforma, nunca en el repo ni en el navegador.
Lo mismo cuando lleguen Stripe y Resend.

## Supabase

Las migraciones viven en `supabase/migrations/` y se aplican con el CLI (`npx supabase@2.117.0 …`,
sin instalar nada global). Un proyecto por entorno: local, staging y producción, cada uno con sus
claves.

**Local** (necesita Docker Desktop):

```powershell
npx --yes supabase@2.117.0 start      # Postgres, Auth, Storage, Studio (54323) y Mailpit (54324)
. .\scripts\dev-env.ps1               # carga las SUPABASE_* del stack local en esta terminal
$env:JOB_HUNTER_DEMO="1"; uvicorn web.main:app --reload --port 8600
```

Los correos de confirmación y de recuperación llegan a Mailpit (`http://127.0.0.1:54324`). Para probar
el store contra la base real: `$env:JH_SUPABASE_TESTS="1"; pytest tests/test_supabase_integration.py`.
Después de cambiar una migración: `npx supabase@2.117.0 db reset` (borra los datos locales).

**Staging / producción:**

1. `npx supabase@2.117.0 login` y crear el proyecto (plan Free para staging; región `sa-east-1`, a
   confirmar según los países de lanzamiento).
2. `npx supabase@2.117.0 link --project-ref <ref>` y `npx supabase@2.117.0 db push`.
3. En *Authentication → URL Configuration*: `Site URL` = la URL pública de la app, y
   `<app>/auth/confirmar` en *Redirect URLs*.
4. En *Authentication → Email Templates*, los enlaces de confirmación y de recuperación apuntan a
   `{{ .SiteURL }}/auth/confirmar?token_hash={{ .TokenHash }}&type=email` (y `type=recovery`), como
   en `supabase/templates/`.
5. **SMTP propio** (Resend) antes de invitar a nadie: el SMTP incluido en Supabase solo envía a los
   miembros del equipo del proyecto y con un tope muy bajo por hora.
6. Cargar las tres `SUPABASE_*` en la plataforma y verificar `/health/ready` → `"database": true`.

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
2. Cargar las variables de entorno de la tabla (con `JH_HTTPS=1` y las `SUPABASE_*` del entorno).
3. Apuntar el chequeo de salud a `/health/ready`.
4. Apuntar `jobhunter.site` al servicio y dejar que la plataforma gestione el certificado.
5. Crear un segundo servicio `staging` desde la misma rama, con sus propias variables.
6. Verificar: `/health/live`, `/health/ready`, el flujo completo en staging y recién después producción.

## Historial

La versión anterior de la interfaz (Streamlit) estuvo publicada en Streamlit Cloud. Ese despliegue se
dio de baja el 24/09/2026 y el código se eliminó del repositorio: hoy el único producto es `web/`.
