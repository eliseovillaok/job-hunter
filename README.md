# JobHunter

Buscar trabajo obliga a repetir la misma búsqueda en un portal tras otro y a leer cientos de avisos que
no tienen que ver con tu experiencia. JobHunter hace ese recorrido por ti: lee tu CV, busca en varios
portales de empleo y te muestra las ofertas que coinciden con tu perfil, **explicando por qué**.

No promete entrevistas ni empleo. Promete que dedicas menos tiempo a buscar y más a postularte a lo que
vale la pena.

## Cómo funciona

1. **Creas tu cuenta y subes tu CV** (PDF, DOCX o TXT), o escribes tu perfil a mano.
2. **La IA lo estructura**: roles, nivel, años, habilidades, idiomas y ubicación, cada dato con la
   frase de tu CV que lo respalda. Lo que tu CV no dice queda como «no especificado».
3. **Revisas y corriges** ese perfil: es tuyo, y es lo que se compara contra cada oferta.
4. **Eliges portales y filtros** (modalidad, ubicaciones, idioma del aviso).
5. **Se busca y se evalúa**: cada oferta recibe una afinidad de 0 a 100 con sus motivos y lo que te
   falta. Los filtros duros descartan antes de gastar IA.
6. **Decides tú**: abrir, guardar o descartar. Si quieres, se genera una carta de presentación para
   una oferta puntual, y puedes recibir el resumen por correo.
7. **Vuelves cuando quieras**: tu perfil, tus preferencias, tu historial de búsquedas y tus ofertas
   guardadas siguen en tu cuenta.

Detalle del cálculo: [docs/scoring.md](docs/scoring.md).

## Lo que el producto no hace

- No inventa experiencia. Si tu CV dice «servicios de AWS», no deduce «EC2, S3, Lambda».
- No entra a portales que exigen iniciar sesión, ni esquiva CAPTCHAs ni límites de acceso. Solo usa
  fuentes públicas o con API.
- No guarda tu clave de Gemini: vive en la sesión del servidor y se borra por inactividad.
- No se postula por ti.

## Requisitos

- **Python 3.12**
- **Supabase** para las cuentas: el stack local del CLI (necesita Docker) o un proyecto en la nube.
  Sin él, solo el modo demo, con cuentas en memoria.
- **Una API key de Google Gemini** ([aistudio.google.com/apikey](https://aistudio.google.com/apikey),
  gratuita con cuota diaria). La pones en la app; no se guarda en ningún lado.
- Opcional: una cuenta de Gmail con contraseña de aplicación, si quieres recibir los resultados por
  correo.

## Instalación y uso

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
npx --yes supabase@2.117.0 start     # Supabase local: base, cuentas, archivos y correos de prueba
. .\scripts\dev-env.ps1              # sus claves, solo en esta terminal
python -m uvicorn web.main:app --reload --port 8600
```

Luego abre `http://localhost:8600`. Los correos de confirmación llegan a `http://127.0.0.1:54324`.

En Linux o macOS es lo mismo, con `python3 -m venv venv` y `source venv/bin/activate`.

### Contra el proyecto de staging en la nube

Para desarrollar contra la base de datos de staging (sin desplegar la app):

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
npx --yes supabase@2.117.0 login     # autenticarse con tu cuenta de Supabase (una sola vez)
npx --yes supabase@2.117.0 link --project-ref ipzowncmuppdhbeffaai  # vincular al proyecto
git fetch && git checkout chore/supabase-staging
# Copiar a mano .env.staging (en .gitignore) desde la otra PC si no lo tenés
# Contiene las claves de Supabase staging y de Resend
# .env.staging: no commitear, agregar a tu gestor de contraseñas
```

Luego, en cada terminal:

```powershell
.\venv\Scripts\Activate.ps1
Get-Content .env.staging | ForEach-Object { if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim()) } }
$env:JOB_HUNTER_DEMO="1"; python -m uvicorn web.main:app --reload --port 8600
```

O en una sola línea (sin el `$env:JOB_HUNTER_DEMO` si querés gastar cuota de Gemini):

```powershell
. .\scripts\dev-env-staging.ps1; $env:JOB_HUNTER_DEMO="1"; python -m uvicorn web.main:app --reload --port 8600
```

Los correos que se envíen van a `onboarding@resend.dev` (sin dominio propio verificado en Resend, es el único destinatario).

### Modo demo

Para ver la interfaz completa sin gastar cuota de Gemini —resultados ficticios, sin red ni IA—:

```powershell
$env:JOB_HUNTER_DEMO="1"; python -m uvicorn web.main:app --reload --port 8600
```

Cualquier clave que empiece con `AIza` sirve en este modo. Si no cargaste las claves de Supabase, las
cuentas viven en memoria y se pierden al reiniciar.

### Como contenedor

```bash
docker build -t jobhunter .
docker run --rm -p 8000:8000 jobhunter
```

Es la misma imagen que irá a producción. Variables de entorno y plataformas: [docs/deploy.md](docs/deploy.md).

### Sin interfaz (línea de comandos)

```bash
python main.py --cv mi_cv.pdf --top-n 20 --dry-run
```

Lee la clave de `GEMINI_API_KEY` en `.env`. Con `--no-email` no envía nada.

## Portales

13 portales de acceso público: Get on Board, LatoJobs, Puente Talent, Remotive, Himalayas, RemoteOK,
WorkingNomads, Arbeitnow, WeWorkRemotely, The Muse, Jobspresso, JustJoin.it y AuthenticJobs.

Cada fuente necesita una base de adquisición documentada —API oficial, feed licenciado o página pública
revisada— antes de entrar. Los portales que pedían iniciar sesión se retiraron del producto.

## Privacidad

- Tu CV se guarda en un almacenamiento privado de tu cuenta (Supabase Storage, con acceso solo para
  ti). Al reemplazarlo o borrarlo se borran el archivo y el perfil que salió de él; al borrar la
  cuenta se borra todo.
- Desde tu cuenta puedes descargar en JSON todo lo que guardamos.
- La API key de Gemini vive solo en memoria del servidor, atada a tu sesión, y se borra tras tres
  horas de inactividad. No se escribe en disco ni en la base.
- A Gemini viaja el texto de tu CV (para estructurarlo) y el texto de las ofertas (para evaluarlas),
  con tu propia clave.
- Los portales reciben las palabras de búsqueda, nada tuyo.
- El correo, si lo activas, se envía desde tu cuenta con tu contraseña de aplicación, que tampoco se
  guarda.

## Estructura del proyecto

| Ruta | Qué hay |
|---|---|
| `web/` | La aplicación: FastAPI + Jinja2 + HTMX (`main.py`, `wizard.py`, `auth.py`, `account.py`, `session.py`, `persist.py`, `supa.py`, `templates/`, `static/`) |
| `supabase/` | Migraciones SQL (tablas, RLS, Storage, plan gratuito) y plantillas de correo de Auth |
| `candidate.py` | CV → perfil estructurado con evidencia |
| `scrapers.py` | Lectura de los portales (APIs y feeds públicos), todo normalizado a `JobPosting` |
| `normalize.py` | Idioma, nivel y modalidad de cada oferta, y deduplicación |
| `matching.py` | Filtros duros, pre-ranking, evaluación por factores y cálculo del score |
| `ai_engine.py` | Acceso a Gemini: JSON con esquema, embeddings, cartas de presentación |
| `eval/` | Perfiles y ofertas ficticios para medir la calidad del matching por profesión |
| `notifier.py` | Resumen por correo, en HTML, con la marca |
| `docs/` | Marca, scoring, hoja de ruta y despliegue |

## Desarrollo

```bash
pytest -q                 # sin red ni IA (las cuentas, en memoria)
JH_SUPABASE_TESTS=1 pytest tests/test_supabase_integration.py   # contra el Supabase local
python -m eval.run        # calidad del matching con Gemini real (consume cuota)
pre-commit install        # detección de secretos en cada commit
```

Antes de tocar algo conviene leer [AGENTS.md](AGENTS.md) (cómo se trabaja en este repo),
[docs/roadmap.md](docs/roadmap.md) (qué se construye ahora y qué no) y
[docs/brand/BRAND.md](docs/brand/BRAND.md) (colores, tipografía y tono antes de cualquier cambio visual).

## Licencia

MIT.
