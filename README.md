# 🎯 Job Hunter — Tu asistente de búsqueda laboral con IA

**Job Hunter** es una aplicación que te ayuda a encontrar ofertas de trabajo que realmente matcheen con tu perfil. Subís tu CV, la IA evalúa cada oferta contra lo que dice tu CV y, si querés, te genera una carta de presentación para la oferta que elijas.

---

## 🎯 ¿Qué problema resuelve?

Buscar trabajo es tedioso:
- 📋 Buscas en múltiples sitios (LinkedIn, Indeed, Remotive, etc.)
- 👀 Lees cientos de ofertas que no matchean con tu perfil
- ✍️ Escribís la misma carta de presentación una y otra vez
- 📧 Organizás ofertas en un Excel desordenado

**Job Hunter** lo automatiza todo:
- 🔍 **Busca automáticamente** en hasta 19 portales
- 🤖 **Evalúa con IA** cada oferta según tu perfil (score 0-100)
- ✍️ **Genera cartas de presentación a pedido**, solo para las ofertas que elijas
- 📧 **Te manda un digest** con los mejores matches al email
- ⏰ **Configúralo una vez** y usalo cuando quieras

---

## ✨ Características principales

### 🔍 Búsqueda automatizada en múltiples plataformas
- **Remotive** — ofertas técnicas remotas curadas
- **Arbeitnow** — base de datos global de trabajo remoto
- **We Work Remotely** — comunidad de 100K+ ofertas remotas
- **Himalayas** — plataforma especializada en talento remoto
- **Get on Board / LatoJobs / Puente / Jobicy** — foco LatAm
- **LinkedIn / Bumeran / Computrabajo / Indeed** — soporte beta con sesión persistente de navegador (aparecen automáticamente al correr la app localmente con Playwright instalado)

### 🤖 Evaluación inteligente con IA
- Cada oferta recibe un **score 0-100** basado en tu perfil
- La IA analiza: habilidades requeridas, experiencia, stack técnico, ubicación
- Filtrá por score mínimo (ej: solo ver ofertas de 65+ puntos)

### ✍️ Cover letters personalizadas
- Pedís la carta desde la oferta que te interesa (no se generan automáticamente)
- Se escribe en el idioma del aviso y usa solo lo que dice tu CV
- Lista para copiar y pegar — solo falta tu firma

### 📧 Digest por email (opcional)
- Recibís un email HTML con los mejores matches
- Acceso desde celular o desktop
- Expandible directamente en el email

### 🎨 Interfaz web intuitiva
- No necesitás tocar código
- Configurá todo desde un formulario en el navegador
- Ves resultados en tiempo real
- Descargá resultados individuales o completos

---

## 📋 Requisitos previos — ¿Qué necesitás?

### Absolutamente necesario:
1. **Una computadora** (Windows, Mac o Linux)
2. **(local - OPCION B) Python 3.10** — [descargá acá](https://www.python.org/downloads/) -- 
3. **Una cuenta de Google** (para la API de Gemini — es **100% gratis**)

### Opcional (solo si querés recibir email):
4. **Una cuenta de Gmail** (con verificación en 2 pasos)

### No necesitás:
- ❌ Pagar nada (Gemini API es gratuita)
- ❌ Conocimientos de programación
- ❌ Servidor propio
- ❌ Instalar nada aparte de Python

---

## 🚀 ¿Cómo empezar?

### Opción A — SIN INSTALAR NADA (Recomendado para probar)

**Entra acá y usá directamente en el navegador:**
### 👉 [https://jobhunter-ia.streamlit.app](https://jobhunter-ia.streamlit.app)

✅ No necesitás instalar nada
✅ Funciona en celular y desktop
✅ Gratis completamente
✅ Tu CV, tu API key y tus resultados no se guardan: viven solo mientras dure tu sesión

**Solo necesitás:**
1. API Key de Gemini (gratis en [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey))
2. Opcional: Gmail App Password (si querés digest por email)

---

### Opción B — INSTALAR EN TU COMPUTADORA (Para uso avanzado)

Si querés correrla localmente en tu máquina, seguí estos pasos:

### Paso 1: Descargar e instalar Python

1. Entra a [python.org/downloads](https://www.python.org/downloads/)
2. Descargá la versión más reciente (3.12 o superior)
3. Ejecutá el instalador
4. **⚠️ IMPORTANTE:** En la primera pantalla, tildá la opción que dice "Add Python to PATH"
5. Click en "Install Now"
6. Esperá a que termine la instalación

**Para verificar que instaló correctamente:**
- En Windows: abrí "Command Prompt" (cmd.exe)
- En Mac/Linux: abrí "Terminal"
- Escribí: `python --version`
- Debería mostrar algo como `Python 3.12.0`

### Paso 2: Descargar Job Hunter

1. Descargá el archivo `job_hunter.zip` desde el repositorio
2. Descomprimilo en una carpeta (ej: `C:\Users\TuUsuario\job_hunter` en Windows, o `~/job_hunter` en Mac/Linux)
3. Abrí una terminal en esa carpeta
   - **Windows:** Click derecho en la carpeta → "Abrir PowerShell aquí"
   - **Mac/Linux:** Click derecho → "Abrir terminal aquí"

### Paso 3: Crear el entorno virtual (venv)

El entorno virtual es como una "carpeta aislada" donde viven las dependencias de Job Hunter sin afectar el resto de tu computadora.

En la terminal, escribí:

```bash
python -m venv venv
```

Esperá a que termine (tarda ~30 segundos).

### Paso 4: Activar el entorno virtual

**En Windows (PowerShell):**
```powershell
venv\Scripts\activate
```

**En Mac/Linux:**
```bash
source venv/bin/activate
```

Si funciona correctamente, deberías ver `(venv)` al inicio de la línea en la terminal.

### Paso 5: Instalar las dependencias

En la terminal (con el venv activado), escribí:

```bash
pip install -r requirements.txt
```

Esto descarga e instala todas las librerías necesarias (streamlit, google-genai, requests, etc.). Tarda ~2 minutos. Verás muchas líneas de texto — es normal.

Si querés usar portales con login desde navegador, instalá además Chromium para Playwright:

```bash
python -m playwright install chromium
```

### Paso 6: Obtener la API Key de Gemini (gratis)

1. Entra a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Iniciá sesión con tu cuenta de Google (creá una si no tenés)
3. Click en el botón azul "Create API Key"
4. Seleccioná "Create API key in new project"
5. Google te genera una clave que empieza con `AIza...`
6. **Copiá la clave completa** (es larga, no la cortes)
7. **Guardala en un lugar seguro** (la vas a necesitar cuando corras la app)

⚠️ **Importante:** Esta clave es como tu contraseña — no la compartas ni la subas a GitHub.

### Paso 7: (Opcional) Obtener Gmail App Password

Solo si querés **recibir las ofertas por email**:

1. Entra a [myaccount.google.com/security](https://myaccount.google.com/security)
2. Asegurate de tener "Verificación en 2 pasos" **activada** (si no, activála)
3. Una vez activada, entra a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. En el dropdown "Seleccionar app", elegí "Mail"
5. En el dropdown "Seleccionar dispositivo", elegí "Windows PC" (o tu sistema operativo)
6. Click en "Generar"
7. Google te muestra un código de **16 caracteres** (sin espacios)
8. **Copiá el código completo**
9. **Guardalo en un lugar seguro**

⚠️ **Importante:** Este código es tan sensible como tu contraseña. No lo compartas.

---

## 📱 Ejecutar la aplicación

### OPCIÓN A — Online (sin instalar)
Simplemente entra a: **[jobhunter-ia.streamlit.app](https://jobhunter-ia.streamlit.app)**

### OPCIÓN B — En tu computadora
Con el entorno virtual activado, escribí en la terminal:

```bash
streamlit run app.py
```

En unos segundos:
1. Se abrirá automáticamente una pestaña en tu navegador
2. Verás una página con un formulario en la izquierda y instrucciones a la derecha
3. ¡Ya podés empezar a configurar!

Si no se abre automáticamente, entra a `http://localhost:8501`

---

## 🎯 Cómo usar la aplicación

### 1. **Configuración inicial (barra izquierda)**

#### 🔑 API Key de Gemini
- Pegá la clave que copiaste de aistudio.google.com
- ⚠️ No la cierres — la necesitás cada vez que usas la app

#### 📧 Email (opcional)
- Si querés recibir el digest por email, completá:
  - **Tu Gmail:** tu dirección completa (ej: tu@gmail.com)
  - **App Password:** el código de 16 caracteres que generaste
  - **Email destino:** donde querés recibir el digest (puede ser el mismo Gmail)

### Portales con login (beta)

Para activar `LinkedIn`, `Bumeran`, `Computrabajo` o `Indeed` desde la app, necesitás guardar una sesión de navegador una sola vez:

#### Paso 1 — Instalar Playwright (si no lo hiciste)

```bash
pip install playwright --break-system-packages
python -m playwright install chromium
```

#### Paso 2 — Guardar sesión por portal

Ejecutá el comando correspondiente al portal que querés activar:

```bash
python browser_login.py linkedin
python browser_login.py bumeran
python browser_login.py computrabajo
python browser_login.py indeed
```

Esto abre una ventana real de Chromium. Iniciá sesión manualmente en esa ventana (usuario + contraseña, verificación de dos pasos si aplica). Cuando termines, volvé a la terminal y presioná `Enter`. La sesión queda guardada en `~/.job-hunter/browser_profiles/`, fuera del repo, para que las cookies nunca se commiteen.

#### Paso 3 — Activar en la app

En el paso de configuración "Fuentes de búsqueda", activá el checkbox del portal deseado. La app usa la sesión guardada automáticamente.

> **Notas importantes:**
> - Este flujo es `beta` — la extracción es best-effort y puede variar según cambios en el HTML de cada sitio.
> - Solo lee listados públicos de vacantes. No automatiza postulaciones, clics ni acciones de cuenta.
> - Si la sesión expira, repetí el `browser_login.py` para renovarla.
> - Indeed bloquea activamente el scraping automatizado. La extracción puede ser parcial o fallar si detecta el bot. Se recomienda usar primero las fuentes sin login.

#### 🔍 Búsqueda
- **Keywords:** palabras clave para buscar (ej: "backend developer", "java spring boot")
  - Una por línea
  - Cuantas más, más ofertas encontrás
- **Score mínimo:** solo muestra ofertas con ese score o superior
  - 65 = recomendado (buen balance)
  - 80+ = solo excelentes matches
  - 50+ = más permisivo
- **Plataformas:** tildá las que querés buscar

#### 👤 Tu perfil
- Describí en español lo que buscás y tu experiencia
- La IA lo usa para evaluar ofertas
- Sé específico: menciona tecnologías, años de experiencia, qué rol buscás

### 2. **Buscar ofertas**
- Click en el botón azul "🚀 Buscar ofertas ahora"
- Verás progreso en tiempo real:
  - Primero: búsqueda en los portales elegidos
  - Luego: evaluación de cada oferta con IA
- **Duración:** depende de cuántos portales y ofertas incluyas; podés detenerla en cualquier momento

### 3. **Ver resultados**
- Se cargan en dos tabs:
  - **🔥 Top matches:** solo ofertas sobre tu score mínimo
  - **📋 Todas:** todas las ofertas encontradas, ordenadas por score

- Por cada oferta ves:
  - **Score:** 0-100 (verde = excelente, amarillo = bueno, gris = bajo)
  - **Plataforma:** dónde se encontró (Remotive, Arbeitnow, etc.)
  - **Razones del match:** qué habilidades tuyas matchean
  - **Skills faltantes:** qué te falta (para que lo sepas)
  - **Carta de presentación:** botón para generarla, solo si la querés
  - **Ver oferta:** link directo al job description

### 4. **Descargar resultados**
- **Cover letter individual:** botón debajo de cada carta
- **Resultados completos:** JSON con todos los datos (al final de la página)

### 5. **Email (opcional)**
- Si completaste el email en la configuración, recibirás un email HTML con los mejores matches
- Expandible desde el celular

---

## ❓ Preguntas frecuentes

### **¿Es completamente gratis?**
Sí. Google Gemini tiene un free tier generoso:
- 15 solicitudes/minuto
- 1.500 solicitudes/día
- $0 USD
- Suficiente para correr el script varias veces al día

Si querés runs ilimitados, podés activar billing en Google Cloud (< $0.01 USD por corrida).

### **¿Qué pasa si me equivoco en la API Key?**
La app te lo va a decir. Volvé a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), generá una nueva clave y pegala de nuevo.

### **¿Mis credenciales se guardan?**
No. En la versión web, la app corre en un servidor: tu API key, tu CV y tus credenciales de email se usan solo durante tu sesión y no se guardan en disco. Se usan para:
- Conectar a la API de Gemini (Google)
- Enviar email (Gmail)

Si corrés la app localmente (Opción B), todo pasa por tu computadora.

### **¿Qué pasa si me olvido el App Password de Gmail?**
Generá uno nuevo en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). El anterior se invalida automáticamente.

### **¿Puedo cambiar las keywords sin reiniciar?**
Sí. Cambialas en la barra izquierda y click en "Buscar ofertas ahora" de nuevo.

### **¿Cuánto tiempo tarda?**
Depende de cuántos portales y ofertas incluyas. La evaluación con IA hace una consulta por oferta, así que con la opción "Limitar cantidad de ofertas" controlás la duración. Podés detener la búsqueda en cualquier momento.

### **¿Qué pasa si no tengo Gmail?**
Podés usar cualquier email. Cuando te pida "Gmail App Password", generá un "App Password" desde las configuraciones de seguridad de tu cuenta de email.

### **¿Funciona offline?**
No. Necesitás conexión a internet para:
- Scrapear las plataformas
- Usar la IA de Gemini
- Enviar emails

### **¿Puedo compartir mi perfil con amigos?**
Sí, pero cada amigo necesita su propia API Key de Gemini. La clave es personal y no se debe compartir.

### **¿Qué modelos de IA están disponibles próximamente?**
Job Hunter está diseñado para aceptar múltiples modelos. Próximamente agregaremos:
- **Claude (Anthropic)** — excelente para análisis
- **GPT-4 (OpenAI)** — muy poderoso pero requiere pago
- **Otros modelos open-source** — alternativas gratuitas

Por ahora solo soporta Gemini porque es gratuito y muy potente.

---

## 🐛 Si algo sale mal

### La app no se abre
```bash
# Asegurate de que el venv está activado (ves "(venv)" en la terminal)
# Luego corre de nuevo:
streamlit run app.py
```

### Error: "API key not valid"
- Copiaste la clave completa? (empieza con "AIza...")
- ¿Es del proyecto correcto en aistudio.google.com?
- Intentá generar una nueva clave

### Error: "Email configuration invalid"
- Verificá que escribiste bien el email
- Verificá que el App Password tiene 16 caracteres (sin espacios)
- Asegurate de tener verificación en 2 pasos activada en Gmail

### Error: "Streamlit DuplicateElementKey"
- Actualiza a la última versión: `pip install --upgrade streamlit`

### Python no se encuentra
- Reinstalá Python y tildá "Add Python to PATH"
- Reiniciá la terminal después de instalar

### La terminal no reconoce comandos
- Probá abriendo "Command Prompt" en lugar de PowerShell (Windows)
- O ejecutá `python -m pip install --upgrade pip` para actualizar

### Necesito más ayuda
- Abrí un issue en GitHub
- O contactá directamente al desarrollador

---

## 📁 ¿Qué archivos se crean?

Cuando corres la app, se crean automáticamente:

```
job_hunter/
├── venv/                 # Tu entorno virtual (no toques)
├── app.py                # La aplicación web
├── config.py             # Archivo de configuración (opcional editar)
├── scrapers.py           # Código para scrapear plataformas
├── ai_engine.py          # Código para evaluar con IA
├── notifier.py           # Código para enviar emails
├── main.py               # Script de línea de comandos (alternativa a app.py)
└── requirements.txt      # Lista de dependencias
```

Los archivos que aparecen como **resultado**:
- `results/` — JSON de cada corrida, **solo si usás `main.py`** (la app web no guarda nada: descargá el JSON desde la página)
- `job_hunter.log` — log de ejecuciones (solo si usás `main.py`)

---

## 🔐 Privacidad y Seguridad

### Qué pasa con tus datos:
- **Versión web:** la app corre en un servidor. Tu CV, API key, credenciales y resultados se usan solo durante tu sesión y no se guardan en disco
- **Versión local:** todo corre en tu computadora
- **Resultados:** los descargás vos como JSON; la app web no los guarda

### Qué información procesa:
- Descripciones de ofertas de los portales (públicas)
- Tu perfil (lo guardás vos)
- API Key de Gemini (nunca se expone)
- App Password de Gmail (nunca se expone)

### Qué se envía fuera:
- Descripción de la oferta + tu perfil → Google Gemini (para evaluar)
- Email → servidores de Gmail (si envías digest)

**Ambas conexiones van encriptadas (HTTPS).** Ojo: en el plan gratuito de la API de Gemini, Google puede usar el contenido enviado para mejorar sus productos. Si no querés que tu CV se use así, usá una API key con facturación activada.

---

## 📝 Licencia

MIT — libre para usar, modificar y distribuir.

---

## 🤝 Contribuciones

¿Encontraste un bug? ¿Tienes una idea?
- Abrí un issue en GitHub
- O contactá directamente al desarrollador

**Ideas de mejoras pendientes:**
- Dashboard web con historial de aplicaciones
- Integración con Google Sheets
- Filtros por salario y seniority
- Notificaciones en tiempo real

---

## 🖥️ Interfaz web nueva (`web/`) — para desarrolladores

La interfaz se está migrando de Streamlit a **FastAPI + Jinja2 + HTMX**, para tener control total del
diseño y poder desplegar en cualquier servidor de Python. El núcleo (CV, portales, matching, IA) es el
mismo para ambas. Mientras dure la migración, la app de Streamlit sigue disponible.

| Interfaz | Comando | Estado |
|---|---|---|
| Streamlit (actual) | `streamlit run app.py` | En producción |
| Web nueva (`web/`) | `uvicorn web.main:app --port 8600` | Landing, resultados y asistente listos |

```powershell
# Desarrollo, con recarga automática y datos ficticios (sin gastar cuota de Gemini)
$env:JOB_HUNTER_DEMO="1"; python -m uvicorn web.main:app --reload --port 8600
```

**Estructura**

| Archivo | Rol |
|---|---|
| `web/main.py` | Rutas de landing y resultados, middleware de sesión y cabeceras de seguridad |
| `web/wizard.py` | Asistente de 4 pasos (CV → acceso a la IA → perfil → búsqueda) |
| `web/session.py` | Estado por usuario en memoria; cookie aleatoria `httponly` |
| `web/settings.py` | Configuración por variables de entorno (ver tabla abajo) |
| `web/portals.py` | Portales disponibles, agrupados por región |
| `web/common.py` | Plantillas, idioma/tema y helpers de marca |
| `web/templates/` · `web/static/` | HTML, CSS y JavaScript (colores desde `docs/brand/tokens.json`) |

**Configuración (variables de entorno)**

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `JOB_HUNTER_DEMO` | — | `1` = datos ficticios y sin IA |
| `JH_SESSION_TTL` | `10800` | Segundos de inactividad antes de borrar la sesión (CV y clave) |
| `JH_MAX_SESSIONS` | `500` | Sesiones simultáneas en memoria |
| `JH_MAX_CV_MB` | `10` | Tamaño máximo del CV |
| `JH_HTTPS` | — | `1` detrás de un proxy TLS: cookie de sesión solo por HTTPS |
| `GEMINI_RPM` | `15` | Llamadas por minuto a Gemini (subir solo con una clave paga) |

**Despliegue**

Sirve cualquier hosting que corra Python (Render, Railway, Fly.io, un VPS). Requisitos:

```bash
pip install -r requirements.txt
uvicorn web.main:app --host 0.0.0.0 --port $PORT
```

- **Un solo proceso (sin `--workers`).** Las sesiones viven en la memoria del proceso: con varios
  workers, un usuario perdería su sesión al caer en otro. Para escalar a varios habrá que mover las
  sesiones a un almacén compartido; hoy no hace falta.
- Detrás de un proxy TLS, definir `JH_HTTPS=1`.
- Con servidor propio también funcionan los portales con inicio de sesión (Playwright), que en
  Streamlit Cloud están deshabilitados.
- No hay base de datos: nada se guarda en disco. Reiniciar el proceso cierra las sesiones abiertas.

---

## 💬 Soporte

¿Preguntas? ¿Sugerencias?
- GitHub: [github.com/eliseovillaok/job-hunter](https://github.com/eliseovillaok/job-hunter)

---

<div align="center">
  Hecho con ☕ y mucha paciencia
</div>
