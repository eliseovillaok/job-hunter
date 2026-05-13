# 🎯 Job Hunter — Automatización de Búsqueda Laboral

Sistema automatizado que encuentra ofertas de trabajo en múltiples plataformas,
las evalúa con IA y genera cover letters personalizadas.

## 📦 Instalación

```bash
# 1. Clonar / descomprimir el proyecto
cd job_hunter

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

## ⚙️ Configuración

Editá `config.py` con tus datos, o definí variables de entorno:

```bash
export ANTHROPIC_API_KEY="sk-ant-TU_CLAVE"
export EMAIL_SENDER="tu_email@gmail.com"
export EMAIL_PASSWORD="tu_app_password_gmail"   # NO la contraseña normal
export EMAIL_RECIPIENT="tu_email@gmail.com"
```

### Obtener Gmail App Password
1. Gmail → Configuración → Seguridad → Verificación en 2 pasos (activar)
2. Buscar "Contraseñas de aplicaciones"
3. Generar una para "Correo / Otro dispositivo"
4. Usar esa contraseña de 16 dígitos en EMAIL_PASSWORD

## 🚀 Uso

```bash
# Correr completo (scraping + IA + email)
python main.py

# Solo ver resultados sin enviar email
python main.py --dry-run

# Correr y guardar en directorio custom
python main.py --output ./mis_resultados
```

## 📅 Automatización con cron (Linux/Mac)

```bash
# Abrir crontab
crontab -e

# Correr todos los días a las 8:00 AM
0 8 * * * cd /ruta/a/job_hunter && /ruta/a/venv/bin/python main.py >> cron.log 2>&1

# Correr Lunes, Miércoles y Viernes a las 9:00 AM
0 9 * * 1,3,5 cd /ruta/a/job_hunter && /ruta/a/venv/bin/python main.py >> cron.log 2>&1
```

## 📅 Automatización con Task Scheduler (Windows)

```powershell
# Crear tarea programada diaria a las 8 AM
schtasks /create /tn "JobHunter" /tr "C:\ruta\venv\Scripts\python.exe C:\ruta\main.py" /sc daily /st 08:00
```

## 📁 Estructura del proyecto

```
job_hunter/
├── main.py          # Orquestador principal
├── config.py        # ⚙️ CONFIGURAR ANTES DE CORRER
├── scrapers.py      # Scrapers de plataformas
├── ai_engine.py     # Scoring y cover letters con Claude
├── notifier.py      # Envío de email HTML
├── requirements.txt
├── results/         # JSONs con historial de runs
└── job_hunter.log   # Log de ejecuciones
```

## 🔧 Personalización

### Ajustar umbral de matching
En `config.py`:
```python
MIN_MATCH_SCORE = 65   # 0–100, subir para filtrar más
```

### Agregar / cambiar keywords
```python
SEARCH_KEYWORDS = [
    "backend developer java",
    "cloud engineer",
    ...
]
```

### Cambiar frecuencia de notificación
Modificar la línea en crontab según necesidad.

## 📧 Ejemplo de email recibido

El email incluye por cada match:
- **Score de compatibilidad** (0–100) con color visual
- **Razones del match** (habilidades, experiencia)
- **Skills faltantes** (para considerar antes de aplicar)
- **Cover letter personalizada** expandible con un click
- **Link directo** a la oferta

## ⚠️ Notas importantes

- LinkedIn y Indeed limitan el scraping agresivo — el script incluye delays
- GetOnBoard y Torre.co tienen APIs más amigables
- Los resultados se guardan en `./results/` para histórico
- Los logs se guardan en `job_hunter.log`
