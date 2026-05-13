# Job Hunter

Automatiza la búsqueda de ofertas remotas, las evalúa con Google Gemini, genera cover letters para los mejores matches y opcionalmente envía un digest por email.

## Qué hace

El flujo real de la aplicación es:

1. Hace scraping de ofertas desde:
   - Remotive
   - Arbeitnow
   - We Work Remotely
   - Himalayas
2. Deduplica resultados.
3. Evalúa cada oferta con Gemini.
4. Genera cover letters solo para las ofertas que superan el umbral `MIN_MATCH_SCORE`.
5. Muestra un resumen en consola.
6. Guarda un archivo JSON en `results/`.
7. Si no se usa `--dry-run` ni `--no-email`, envía un email HTML con los matches.

## Requisitos

- Python 3.12 o compatible con las dependencias instaladas
- Una API key de Google Gemini
- Una cuenta de email SMTP compatible con la configuración actual

## Instalación

```bash
cd job_hunter
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

En Windows:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

La app toma configuración desde variables de entorno, con fallback a los valores de `config.py`.

Variables relevantes:

```bash
export GEMINI_API_KEY="TU_API_KEY_DE_GEMINI"
export EMAIL_SENDER="tu_email@gmail.com"
export EMAIL_PASSWORD="tu_app_password"
export EMAIL_RECIPIENT="tu_email@gmail.com"
```

La variable correcta para la IA es `GEMINI_API_KEY`.
La aplicación no usa `ANTHROPIC_API_KEY`.

### Qué hay en `config.py`

En [config.py](/home/user/proyectos/job_hunter/config.py:1) puedes ajustar:

- `SEARCH_KEYWORDS`: keywords de búsqueda
- `ONLY_REMOTE`: filtra solo remoto
- `MIN_MATCH_SCORE`: umbral mínimo para generar cover letters y enviar digest
- `CANDIDATE_PROFILE`: perfil usado por Gemini
- `SMTP_HOST` y `SMTP_PORT`: servidor SMTP

## Cómo ejecutar

### Ejecución normal

Hace scraping, scoring con IA, genera cover letters, guarda resultados y envía email si hay matches.

```bash
python main.py
```

### Modo sin envío de email

Hace todo menos enviar email. Igual genera cover letters y guarda el JSON.

```bash
python main.py --no-email
```

### Modo dry run

No envía email. Igual hace scraping, scoring, cover letters, resumen y guardado de resultados.

```bash
python main.py --dry-run
```

### Directorio de salida personalizado

El JSON de resultados se guarda por defecto en `./results`. Puedes cambiarlo:

```bash
python main.py --output ./mis_resultados
```

También puedes combinar opciones:

```bash
python main.py --dry-run --output ./mis_resultados
```

## Salidas generadas

- `results/results_YYYYMMDD_HHMM.json`: resumen estructurado del run
- `job_hunter.log`: log de ejecución

Cada JSON guardado incluye:

- score
- title
- company
- source
- url
- remote
- match_reasons
- missing_skills
- summary
- has_cover_letter

## Cómo funciona el email

El digest se envía solo si:

- no usas `--dry-run`
- no usas `--no-email`
- existen ofertas con score suficiente como para generar cover letter

Si no hay matches suficientes, no se envía email.

## Obtener credenciales

### Gemini API Key

La propia configuración del proyecto apunta a Google AI Studio:

https://aistudio.google.com/app/apikey

### Gmail App Password

Si usas Gmail:

1. Activa verificación en dos pasos.
2. Crea una App Password.
3. Usa esa contraseña en `EMAIL_PASSWORD`.

## Estructura del proyecto

```text
job_hunter/
├── main.py
├── config.py
├── ai_engine.py
├── scrapers.py
├── notifier.py
├── requirements.txt
├── results/
└── job_hunter.log
```

## Dependencias

Según [requirements.txt](/home/user/proyectos/job_hunter/requirements.txt:1), la app usa:

- `google-genai`
- `requests`
- `feedparser`

## Notas

- La evaluación de IA usa Gemini, no Claude.
- El modelo configurado en el código actual es `models/gemini-2.0-flash-lite`.
- Los delays y reintentos están implementados en el código para reducir problemas de rate limit.
- Los scrapers dependen de APIs y feeds externos; si una fuente cambia, puede devolver menos resultados o fallar.
