# Arquitectura y flujo de desarrollo — JobHunter

Documento para entender qué es JobHunter, cómo está construido y cómo trabajar en él.

## ¿Qué es JobHunter?

Un MVP (mínimo producto viable) que:
1. Te pide crear una cuenta.
2. Lees tu CV.
3. Lo estructura con IA (Gemini).
4. Busca ofertas en 13 portales públicos de empleo.
5. Compara cada oferta con tu perfil (score 0–100 + razones).
6. Muestra las más relevantes.
7. Guardas, descartás o generás carta de presentación para cada una.
8. Todo queda en tu cuenta.

**Sin despliegue público todavía:** lo probás en local. La salida a producción es Fase 2.

---

## Arquitectura: monolito modular en Python

```
una sola app FastAPI (servidor web)
        ↓
    Supabase (base de datos, autenticación, almacenamiento de CVs)
        ↓
   Gemini (IA para estructurar CV y comparar ofertas)
```

**No hay:** microservicios, colas de tareas, workers, Kubernetes. Una sola instancia del servidor, una base de datos, sesiones en memoria.

### Capas del código

```
web/                     — La aplicación web (FastAPI + Jinja2 + HTMX)
├── main.py              — Landing, login, logout, rutas globales
├── auth.py              — Crear cuenta, ingresar, recuperar contraseña
├── account.py           — Tu perfil, historial, export, borrado
├── wizard.py            — Asistente de 4 pasos (CV → perfil → búsqueda)
├── run.py               — La búsqueda: despacha a portales, compara, guarda
├── session.py           — Estado en memoria (cuánta batería, qué cookies)
├── persist.py           — Contrato del almacenamiento (la app no sabe si es local o Supabase)
├── supa.py              — La implementación en Supabase (HTTP, sin librerías raras)
├── csrf.py              — CSRF token en cada acción que modifica datos
├── settings.py          — Variables de entorno (claves, URLs, límites)
└── templates/           — HTML (Jinja2, sin JavaScript casi)

supabase/
├── migrations/          — Cambios a la base de datos (versionados, idempotentes)
├── config.toml          — Configuración de Auth, SMTP, plantillas de correo
└── templates/           — Plantillas de correo (confirmación, recuperación)

scrapers.py              — Leer ofertas de los 13 portales
normalize.py             — Idioma, nivel, modalidad de cada oferta
candidate.py             — Estructurar el CV en un perfil
matching.py              — Comparar perfil con ofertas, calcular score
ai_engine.py             — Hablar con Gemini (JSON, embeddings, cartas)
eval/                    — Tests de calidad del matching

tests/
├── conftest.py          — Fixtures, cuentas fake para los tests
└── test_*.py            — Tests unitarios e integración
```

---

## Supabase: la base de datos y más

Supabase es una interfaz amigable sobre PostgreSQL que te da gratis:

1. **Base de datos (Postgres):** tablas, filas, consultas SQL.
2. **Autenticación (Auth):** crear cuenta, ingresar, confirmar mail, recuperar contraseña.
3. **Almacenamiento de archivos (Storage):** privado (tu CV solo lo ves vos), con acceso por JWT.
4. **Edge Functions:** código que corre en la nube (todavía no lo usamos).

**En JobHunter:**
- Las tablas viven en `supabase/migrations/`: `profiles`, `cv_documents`, `candidate_profiles`, `search_runs`, `saved_jobs`, etc.
- Auth maneja los usuarios: crear, confirmar mail, ingresar.
- Storage guarda tus CVs en una carpeta privada.
- RLS (Row-Level Security) asegura que un usuario solo vea su propio CV, su propio perfil.

**Tres ambientes:**

| Ambiente | Dónde | Para qué |
|----------|-------|----------|
| **Local** | Tu PC, Docker | Desarrollo: cambias código y ves los resultados al instante |
| **Staging** | Nube Supabase (gratis) | Pruebas pre-producción: la base de datos en la nube, pero la app sigue en local |
| **Producción** | Nube (Railway o Render) + Supabase | Usuarios reales (todavía no existe) |

---

## Lo que hicimos en esta sesión

### 1. Verificar que Fase 1 estaba lista

- **Rama:** `feat/phase-1-accounts` (ya estaba hecha, solo checkeamos).
- **Tests:** 193 en local, 6 contra Supabase local.
- **Flujo:** crear cuenta → confirmar mail → asistente → búsqueda → guardar/descartar → historial → export → borrar.

### 2. Mergear a main

- Abrimos PR #1, CI pasó en verde.
- **Regla nueva:** mergear con `gh pr merge --rebase --delete-branch`. Sin merge commits, historial lineal, rama se borra automáticamente. Actualizado en `AGENTS.md` y en GitHub.

### 3. Crear staging en la nube

**Problema:** los tests de integración pasaban en local, pero sin una base de datos en la nube no podíamos probar:
- ¿Las plantillas de correo salen bien?
- ¿Resend recibe los correos?
- ¿Los dominios en las URLs del navegador funcionan en AWS (no localhost)?

**Solución:**

1. **Crear proyecto de Supabase:**
   ```powershell
   npx supabase@2.117.0 login                           # tu cuenta
   npx supabase@2.117.0 projects create jobhunter-staging \
     --org-id ofskjyhuugqyemjklgww \
     --region us-east-1 \
     --db-password <password-random>
   ```
   → Proyecto `jobhunter-staging`, ref `ipzowncmuppdhbeffaai`, plan Free, región Virginia.

2. **Vincular el proyecto a tu copia local del repo:**
   ```powershell
   npx supabase@2.117.0 link --project-ref ipzowncmuppdhbeffaai
   ```
   → Crea un archivo `.supabase/config.json` (local, no en git).

3. **Empujar la migración:**
   ```powershell
   npx supabase@2.117.0 db push
   ```
   → Aplica `supabase/migrations/20260924182859_phase1_accounts.sql` en la nube. Tabla de usuarios, CV privado, RLS, todo.

4. **Configurar Auth (correos, SMTP, URLs):**
   - Agregamos un bloque `[remotes.staging]` en `supabase/config.toml`.
   - Hereda todo de local (plantillas, configuración), pero cambia:
     - `site_url = "http://localhost:8600"` (todavía probamos desde la app local).
     - `additional_redirect_urls` apuntan a `/auth/confirmar`.
     - SMTP de Resend en lugar del local:
       ```toml
       [remotes.staging.auth.email.smtp]
       enabled = true
       host = "smtp.resend.com"
       port = 465
       user = "resend"
       pass = "env(RESEND_API_KEY)"
       ```
     - Límites relajados: 30 correos por hora en staging (en local es 2, para debug).
   
   ```powershell
   npx supabase@2.117.0 config push    # sube la configuración a la nube
   ```

5. **Guardar las claves en `.env.staging` (no en git):**
   ```
   SUPABASE_DB_PASSWORD=...
   RESEND_API_KEY=...
   SUPABASE_URL=https://ipzowncmuppdhbeffaai.supabase.co
   SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
   SUPABASE_SECRET_KEY=sb_secret_...
   ```
   - `.env.staging` está en `.gitignore`: **no commitear secretos**.

### 4. Probar contra staging

Los 6 tests de integración pasan contra la nube:
- Crear usuario por API de administración.
- Guardar CV en Storage.
- Contar búsquedas contra el cupo.
- Borrar la cuenta y limpiar todo.

Levantamos la app local contra staging y te dimos los pasos para:
- Crear cuenta real con tu mail.
- Confirmar con el correo que llega desde `onboarding@resend.dev`.
- Completar el asistente y buscar.
- Guardar/descartar ofertas.
- Historial, export, borrado.

### 5. Documentación

Actualizar README, `deploy.md` y `roadmap.md`:
- Cambiar de `sa-east-1` a `us-east-1`.
- Agregar instrucciones: cómo levantar contra staging en una línea.
- Crear `scripts/dev-env-staging.ps1` para cargar las claves.
- Marcar staging como ✅ hecho en la hoja de ruta.

---

## Flujo de trabajo: de local a staging a producción

### Desarrollo en local

```powershell
npx supabase@2.117.0 start                    # base local (Docker)
. .\scripts\dev-env.ps1                       # carga claves locales
$env:JOB_HUNTER_DEMO="1"
python -m uvicorn web.main:app --reload --port 8600
```

- Base en localhost, sin internet.
- Cambias código, la app recarga sola.
- Los correos llegan a Mailpit (`127.0.0.1:54324`).

### Probar contra staging

```powershell
. .\scripts\dev-env-staging.ps1               # carga claves staging desde .env.staging
$env:JOB_HUNTER_DEMO="1"
python -m uvicorn web.main:app --reload --port 8600
```

- Base en la nube (Supabase staging).
- La app sigue en tu PC.
- Los correos salen de verdad a Resend.
- **Caso de uso:** probar correos, flujo de Auth, cambios en la base antes de producción.

### Producción (próximamente, Fase 2)

```
git push origin main
       ↓
  GitHub Actions (tests)
       ↓
  Railway o Render (despliega automático)
       ↓
  jobhunter.site (dominio público)
```

- La app y la base de datos están en la nube.
- Usuarios reales.

---

## Cómo Supabase Auth funciona en JobHunter

### Crear cuenta (sign up)

1. Tipeás mail y contraseña en `/crear-cuenta`.
2. `web/auth.py` → POST a `https://<ref>.supabase.co/auth/v1/signup`.
3. Supabase crea el usuario en su tabla interna, **pero no está confirmado todavía**.
4. Supabase envía un correo de confirmación vía SMTP (Resend en staging, Mailpit en local).
5. El correo tiene un link a `localhost:8600/auth/confirmar?token_hash=...&type=email`.

### Confirmar mail

1. Tocás el link del correo.
2. `web/auth.py` → GET `/auth/confirmar?token_hash=...` → envía el token a Supabase.
3. Supabase marca el usuario como confirmado y devuelve una sesión (JWT).
4. Guardamos la sesión en una cookie httponly (no accesible desde JavaScript).
5. Sos redirigido a `/asistente` (el primer paso del asistente).

### Ingresar (sign in)

1. Tipeás mail y contraseña en `/ingresar`.
2. `web/auth.py` → POST a `/auth/v1/signin` con mail y contraseña.
3. Supabase valida y devuelve una sesión (JWT).
4. Guardamos la sesión en una cookie httponly.
5. Sos redirigido a `/asistente` o a donde ibas antes.

### Salir (sign out)

1. Tocás Salir.
2. `web/auth.py` → POST `/salir`.
3. Borramos la cookie de sesión (sin hablar con Supabase; el token expira solo).
4. Sos redirigido a `/`.

---

## Cómo el CV se estructura con IA

### Flujo en el asistente

**Paso 1:** Cargar el CV (PDF, DOCX, TXT) o escribir el perfil manualmente.
- El archivo se guarda en Supabase Storage (privado, solo vos lo ves).
- El contenido se extrae (PDF → texto).

**Paso 2:** Pasar el texto a Gemini.
- `candidate.py` → `extract_profile(cv_text)` → Gemini con este prompt:
  ```
  Estructura este CV: roles, años, nivel, habilidades, idiomas, ubicación.
  Cada dato debe decir de dónde del CV sale. Si falta, di "no especificado".
  Responde en JSON.
  ```
- Gemini responde con un JSON de `CandidateProfile`.

**Paso 3:** Mostramos el perfil en el asistente, editable.
- Ves lo que IA infirió.
- Corregís lo que esté mal.
- Guardamos el perfil en `candidate_profiles` (tabla de la base).

### El perfil NO se usa directamente

El perfil es solo el intermediario. Lo que se usa para comparar ofertas es:
- **Extracto de búsqueda:** palabras clave (en ES e EN), nivel, modalidad.
- **Embeddings:** vectores de los nombres de las habilidades (para comparación semántica con las ofertas).

Esto vive en `search_preferences`.

---

## Cómo se comparan ofertas con tu perfil

### Flujo en la búsqueda

**1. Scrapers:** leer los portales
- `scrapers.py` → 13 funciones, una por portal.
- Cada una devuelve una lista de `JobPosting` (título, empresa, descripción, ubicación, modalidad, enlace).

**2. Normalización:** entender la oferta
- `normalize.py` → idioma (ES/EN), nivel (junior/mid/senior), modalidad (remoto/híbrido/presencial).
- Todo sin IA, por patrones.

**3. Filtros duros (antes de la IA):** descartar rápido
- Tu preferencia: "modalidad remota, nivel mid, ubicaciones LATAM".
- Se descartan todas las ofertas que no cumplan → **no gastan IA**.

**4. Pre-ranking con embeddings:** ordenar por semejanza
- Tu perfil tiene embeddings de tus habilidades.
- Las ofertas tienen embeddings de las habilidades que piden.
- Calculamos similitud coseno (0-1).
- Las mejores K van al siguiente paso (para no gastar cuota).

**5. Evaluación por Gemini:** el score final
- `matching.py` → `compute_score(candidato, oferta, gemini)`.
- Gemini evalúa **5 factores:**
  1. Match de habilidades técnicas.
  2. Experiencia en el sector.
  3. Alineación de seniority.
  4. Aceptabilidad de la modalidad y la ubicación.
  5. Motivación potencial (basada en descripción).
- Cada factor es 0-20.
- **El código** suma con pesos fijos (`matching.WEIGHTS`) → score 0-100.
- Gemini también explica los motivos.

**6. Guardar o descartar**
- Guardas la oferta → se guarda en `saved_jobs`.
- Descartás → se borra (no vuelve a aparecer).

---

## Tabla de comandos por situación

### Quiero cambiar el código y probar en local

```powershell
# Terminal 1: base de datos
npx supabase@2.117.0 start

# Terminal 2: app
. .\scripts\dev-env.ps1
python -m uvicorn web.main:app --reload --port 8600
```

Luego tocá algo en el código → la app recarga sola → actualizá el navegador.

### Quiero probar contra staging (la nube)

```powershell
# Primero, una sola vez:
npx supabase@2.117.0 login
npx supabase@2.117.0 link --project-ref ipzowncmuppdhbeffaai

# Después, en cada sesión:
. .\scripts\dev-env-staging.ps1
$env:JOB_HUNTER_DEMO="1"
python -m uvicorn web.main:app --reload --port 8600
```

Los cambios en el código aplican al instante (recarga). Los datos se guardan en la nube.

### Quiero probar los tests

```powershell
# Tests locales (sin red ni IA, base en memoria)
pytest -q

# Tests contra Supabase local
npx supabase@2.117.0 start   # en otra terminal
$env:JH_SUPABASE_TESTS="1"; pytest tests/test_supabase_integration.py -q
```

### Quiero empujar cambios

```powershell
# Cambios chicos, bien definidos
git add .
git commit -m "feat: descripción breve"
git push origin <rama>

# Después:
# Abrir PR → CI pasa → rebase and merge desde el GitHub → rama se borra automática
```

---

## Resumen: de dónde salen los datos

```
Tu CV (PDF/TXT)
    ↓
  [Gemini]  → estructura el perfil
    ↓
Tu perfil editable
    ↓
Supabase (tabla candidate_profiles)
    ↓
Tu búsqueda (portales + filtros)
    ↓
Scrapers → 13 portales
    ↓
Ofertas normalizadas
    ↓
Filtros duros → descartan ofertas que no cumplen tu region/nivel/modalidad
    ↓
Embeddings → pre-ranking por semejanza técnica (sin IA)
    ↓
[Gemini]  → evalúa los mejores → score + motivos
    ↓
Resultados ordenados (0-100, explicables)
    ↓
Guardás/descartás
    ↓
Supabase (tabla saved_jobs)
    ↓
Tu historial persiste (próxima vez que entrés, sigue ahí)
```

---

## Siguiente paso: pulir detalles visuales (Fase 1 cierre)

Tenés la rama `chore/supabase-staging` con:
- ✅ Staging listo en la nube.
- ✅ Tests pasando.
- ✅ Documentación actualizada.
- ⏳ Detalles visuales y de funcionamiento que querés acomodar.

Cuando estén listos, abrimos PR, mergear con rebase, y Fase 1 cierra.

---

## Dudas frecuentes

**¿Por qué Supabase y no Firebase?**
- Supabase es PostgreSQL + IA-friendly (no obliga a un esquema rígido).
- Open source (podrías migrar si necesitás).
- SMTP propio (importante para los correos).

**¿Cómo se protege el CV?**
- Se guarda en Supabase Storage, con RLS: solo vos lo lees.
- La IA (Gemini) no ve el archivo, solo el texto. Con tu propia clave.
- Al reemplazar o borrar el CV, se borra el archivo y el perfil derivado.

**¿Qué pasa si me cierro la app a mitad del asistente?**
- Las respuestas del asistente se guardan en `search_preferences` (tabla).
- Al volver, se recuperan desde la base.
- El CV también persiste en Storage.

**¿Cómo se evita que JobHunter sea lento?**
- Filtro determinista antes de IA (no todas las ofertas se evalúan).
- Pre-ranking con embeddings (más rápido que Gemini).
- Un máximo de K ofertas van a Gemini por búsqueda.
- Supabase tiene caché automático.

**¿Cómo se gestiona el cupo de Gemini?**
- Tienes límites de `GEMINI_RPM` y `GEMINI_EMBED_RPM` (llamadas por minuto).
- Además: límites del plan Free en `search_runs` (búsquedas por mes).
- Cada búsqueda **consume un cupo** del mes, aunque no encuentre nada.

**¿Y los portales que necesitan login?**
- Se retiraron del producto. La spec prohíbe cualquier fuente detrás de un login, CAPTCHA o control de acceso.
- Usamos APIs públicas o feeds licenciados.

**¿Cuándo puedo invitar a amigos a probar?**
- En Fase 2, cuando esté en producción con dominio.
- En staging, solo tú (sin dominio verificado en Resend, los correos solo te llegan a ti).

---
