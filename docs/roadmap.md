# Hoja de ruta — JobHunter

Documento vivo. Se revisa al cerrar cada fase.

Ordena en el tiempo lo que la especificación maestra (`docs/private/SPEC-v2.md`, §24 y §30.9) define
como destino. Ante un conflicto manda la spec; este archivo dice **cuándo** y **con qué evidencia**.

## Principios

1. **Usuarios reales antes que features.** Cada fase termina con algo que alguien usa, no con código guardado.
2. **Pasar de fase por evidencia, no por calendario.** Cada fase tiene un disparador medible.
3. **Una persona, un monolito.** Nada de microservicios, colas propias ni reescrituras preventivas.
4. **Medir la calidad siempre.** El eval (`python -m eval.run`) corre antes y después de tocar prompts, pesos o normalización.
5. **Cada cambio es reversible y chico.** Si algo empeora el eval o el feedback, se revierte.
6. **Legal desde el principio.** Ninguna fuente detrás de un login, un CAPTCHA o un límite de acceso (spec §21.9, §34).
7. **Nada de costo variable sin medirlo.** La IA es el mayor riesgo de margen: filtro determinista antes del análisis semántico.

## Dónde estamos

| Hecho | Detalle |
|---|---|
| Núcleo | CV → perfil editable con evidencia · filtros duros · pre-ranking con embeddings · evaluación híbrida por factores · score explicable · tests + CI · eval por profesión (NDCG@5 medio 0.97, sin sesgo tech) |
| UI nueva (`web/`) | FastAPI + Jinja + HTMX: landing, asistente de 4 pasos, resultados con datos demo, sesión por usuario en memoria |
| Fuentes | 14 portales de acceso público. Los que pedían inicio de sesión se retiraron del pipeline; Jobicy salió el 24/09/2026 porque su API dejó de existir |

Lo que **no** existe todavía: base de datos, cuentas, pagos, automatización, despliegue propio.
La clave de Gemini la pone el usuario; en la fase de cobros pasa a ser nuestra y se vuelve un costo a controlar.

---

## Fase 0 — Terminar la UI nueva y dejar la base lista (en curso)

**Objetivo:** el flujo completo corre sobre `web/` en local y Streamlit sale de escena.

- [x] Búsqueda real en segundo plano con pantalla de progreso (fases + estado por portal) y resultados en la sesión.
- [ ] Retirar `app.py`, `theme.py` y `ui.py`; dejar `web/` como única interfaz.
- [ ] Dar de baja el despliegue en Streamlit Cloud.
- [x] `Dockerfile` + `/health/live` y `/health/ready` + configuración por variables de entorno (lista para Railway o Render).
- [x] README reescrito: una sola app, instalación, desarrollo y despliegue.
- [ ] GetOnBoard por su API pública (en una corrida real tardó 5 minutos él solo).

**Listo cuando:** `uvicorn web.main:app` hace CV → perfil → búsqueda real → resultados, y la imagen levanta igual en un contenedor limpio.

## Fase 1 — Persistencia y cuentas

**Objetivo:** el trabajo del usuario sobrevive a cerrar el navegador.

- [ ] Proyecto Supabase (local/staging/producción separados). *Requiere OK antes de sumar el servicio.*
- [ ] Migraciones versionadas: `profiles`, `cv_documents`, `candidate_profiles`, `search_preferences` (spec §6.2).
- [ ] Sesiones por cookie httponly + CSRF en toda acción que modifica estado (spec §7).
- [ ] Alta, ingreso, salida y borrado de cuenta con su flujo completo (spec §4.4, §21.17).
- [ ] Historial de búsquedas (`search_runs`) y ofertas guardadas/descartadas.
- [ ] Límites por uso (todavía sin cobrar): búsquedas por mes, portales, resultados por búsqueda.

**Listo cuando:** una persona se registra, se va, vuelve al otro día y encuentra su perfil y su historial.

## Fase 2 — Producción propia

**Objetivo:** desplegar desde git, con dominio y salud verificable.

- [ ] Elegir Railway o Render y comprometerse con uno (spec §15.4; comparación en [docs/deploy.md](deploy.md)).
- [ ] Entornos `staging` y `production` con secretos separados.
- [ ] `jobhunter.site` apuntando a producción, HTTPS gestionado por la plataforma.
- [ ] Logs estructurados con `trace_id` y despliegue continuo desde `main` con CI en verde.

**Listo cuando:** un push a `main` llega a producción solo, y un chequeo de salud falla si la app no está sana.

## Fase 3 — Inventario de ofertas

**Objetivo:** la misma oferta deja de ser nueva cada vez.

- [ ] `job_sources` y `job_offers` con huella canónica única y deduplicación determinista (spec §9.5).
- [ ] Estado de salud por portal: activo, degradado, pausado, bloqueado, retirado — y apagado manual.
- [ ] Registro por fuente: método de adquisición, permiso, campos guardados, fecha de revisión (spec §21.10).
- [ ] Guardar lo mínimo de cada oferta y enlazar siempre al original.

**Listo cuando:** repetir una búsqueda distingue lo nuevo de lo ya visto, y un portal caído se ve como tal.

## Fase 4 — Matching v1 persistido

**Objetivo:** cada score queda guardado, explicado y auditable.

- [ ] `job_matches` con desglose, evidencia y proveedor/modelo/versión del momento (spec §10.4, §10.6).
- [ ] Caché de evaluaciones por (oferta, versión del perfil): repetir búsquedas no gasta cuota.
- [ ] Feedback por oferta (👍/👎 + motivo corto) guardado como señal.
- [ ] Eval con casos reales anonimizados; métricas por profesión, país e idioma.
- [ ] Revisar los pesos contra la propuesta de la spec §10.2 **con el eval corrido antes y después**.

**Listo cuando:** dos corridas con el mismo perfil y la misma oferta dan el mismo score, y se puede decir con qué versión se calculó.

## Fase 5 — Automatización y correo propio

**Objetivo:** el producto trabaja cuando el usuario no está.

- [ ] Búsquedas recurrentes: `next_run_at` en UTC por usuario, con su zona horaria aparte.
- [ ] Un solo horario central que despacha a los usuarios que tocan (spec §12.3), sin un cron por persona.
- [ ] Resend para el correo transaccional, con clave de deduplicación por envío (spec §14.2).
- [ ] Retirar el envío por SMTP con contraseña de aplicación del usuario: deja de pedirse en el asistente.
- [ ] Umbral de afinidad configurable y pausa de la automatización.

**Listo cuando:** un usuario con automatización activa recibe como mucho un resumen por ciclo, y se puede ver por qué falló uno.

## Fase 6 — Cobros

**Objetivo:** cobrar sin que el navegador pueda mentir.

- [ ] Catálogo de planes y límites en base de datos; nunca un precio incrustado en la lógica (spec §3.4).
- [ ] Entitlements derivados de la suscripción interna, no de un booleano en el perfil (spec §3.3).
- [ ] `webhook_events` con identidad única del evento y procesamiento idempotente (spec §13.1).
- [ ] Stripe primero (Checkout + portal del cliente); Mercado Pago según el mercado de lanzamiento.
- [ ] Trabajo de reconciliación: comparar estado local contra el proveedor (spec §27).

**Listo cuando:** un webhook duplicado, fuera de orden o perdido no corrompe el acceso de nadie.

## Fase 7 — Beta

**Objetivo:** saber si el producto vale lo que cuesta.

- [ ] 10–15 personas de profesiones distintas usándolo con acompañamiento, y después 50.
- [ ] Métricas de activación y retención (spec §23), no visitas.
- [ ] Experimento de precio con una cohorte chica.
- [ ] Página de privacidad, términos y política de reembolso publicadas antes de cobrar (spec §21.23).

**Listo cuando:** hay gente que vuelve porque el sistema encontró algo sin que ella repitiera la búsqueda.

## Fase 8 — Globalización

Solo con señales de mercado: localización, fuentes por país, precios por mercado, SEO, referidos.

---

## Decisiones abiertas

Las que bloquean fases están en la spec §32 (países de lanzamiento, precio, límites del plan gratuito,
estructura de cobro por mercado, retención de CV, proveedor de IA, permisos por fuente). Cuando una se
decide, se actualiza la spec y sube su versión: el código no puede ser el único lugar donde viva.

## Fuera de alcance por ahora

Apps nativas, extensión de navegador, postulación automática, armador de CV, funciones para empleadores,
planes enterprise, microservicios, Kubernetes, data warehouse (spec §25 P2 y §21.16).
