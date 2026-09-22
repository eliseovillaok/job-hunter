# Hoja de ruta — Job Hunter

Documento vivo. Se revisa al cerrar cada etapa.

## Principios

1. **Usuarios reales antes que features.** Cada etapa termina con algo que alguien usa, no con código guardado.
2. **Pasar de etapa por evidencia, no por calendario.** Cada etapa tiene un disparador medible.
3. **$0 hasta que haya retención.** Free tiers (Streamlit Cloud, Gemini, Supabase) hasta la etapa de monetización.
4. **Una persona, un monolito.** Nada de microservicios, colas ni reescrituras preventivas.
5. **Medir la calidad siempre.** El eval (`python -m eval.run`) corre antes y después de tocar prompts, pesos o normalización.
6. **Cada cambio es reversible y chico.** Releases semanales; si algo empeora el eval o el feedback, se revierte.

## Dónde estamos

| Hecho | Detalle |
|---|---|
| Fase 0 | i18n sin recarga, sin estado global entre usuarios, promesas honestas, cartas a pedido |
| Fase 1 | CV → perfil editable con evidencia · filtros · pre-ranking · evaluación híbrida por factores · score explicable · tests + CI · eval por profesión (NDCG@5 medio 0.97, sin sesgo tech) |

---

## Etapa 0 — Cerrar la Fase 1 y salir (esta semana)

**Objetivo:** la versión nueva en producción, validada.

- [ ] Prueba de la interfaz con key real (subir CV ficticio → editar perfil → buscar → ver desglose).
- [ ] Eval `--mode hybrid` vs `--mode single` cuando se renueve la cuota diaria; ajustar `RECHECK_TOP` si hace falta.
- [ ] Push a `main` → redeploy en Streamlit Cloud → prueba rápida en producción.
- [ ] Aplicar la paleta ([docs/brand/palette.svg](brand/palette.svg)) como tokens CSS en la app actual, sin rediseñar.
- [ ] Rotar la API key que quedó en el chat.

**Listo cuando:** producción corre la versión nueva y una búsqueda completa funciona de punta a punta.

## Etapa 1 — Beta con usuarios reales (semanas 1–4)

**Objetivo:** 20–30 personas de **profesiones distintas** hacen al menos una búsqueda y nos dicen qué sirvió.

Solo lo necesario para aprender:
- **Feedback por oferta:** 👍 / 👎 + motivo corto ("no es mi rubro", "pide más experiencia", "ubicación", "otro").
  Arranque sin infraestructura: los eventos se exportan en el JSON y un formulario externo (Tally / Google Forms)
  para comentarios generales.
- **Pulido de lo que más molesta:** los hacks de CSS más visibles, mensajes de error claros, móvil usable.
- **GetOnBoard por su API pública** (hoy tarda ~90 s por 8 ofertas).
- **Página de privacidad** simple y honesta (qué se envía a Gemini, qué no se guarda).
- **Métricas mínimas:** búsquedas completadas, % con al menos una oferta útil, tiempo por búsqueda, errores.

**No hacer todavía:** cuentas, base de datos, pagos, alertas, migrar el frontend.

**Disparador para la Etapa 2:** usuarios que vuelven a buscar o que piden guardar ofertas, o más de 50 búsquedas por semana.

## Etapa 2 — Aprender de los usuarios (meses 2–3)

**Objetivo:** que cada búsqueda deje datos que mejoren la siguiente.

- **Persistencia mínima** (Supabase free: Postgres + login por email con magic link): guardar/descartar ofertas,
  "ya vistas", historial de feedback. *Requiere OK antes de sumar el servicio.*
- **Caché de evaluaciones** por (oferta, versión del perfil): repetir búsquedas no gasta cuota.
- **Eval con casos reales:** los 👍/👎 (anonimizados y con consentimiento) se suman al dataset; métricas por
  profesión, país e idioma.
- **Normalización con ESCO** (gratis, multilingüe): sinónimos de títulos para los términos de búsqueda
  ("contador" = "contable" = "accountant") y skills relacionadas.

**Disparador para la Etapa 3:** el feedback marca "pocas ofertas" o "ofertas viejas" como problema principal.

## Etapa 3 — Más y mejores ofertas (meses 3–5)

**Objetivo:** cobertura real para cualquier profesión y país objetivo.

- **Agregadores con API oficial** (Adzuna, Jooble; free tiers) y **ATS públicos** (Greenhouse, Lever, Ashby).
- **Extracción de requisitos por oferta, una sola vez** (obligatorios, deseables, años, licencias, idioma,
  restricciones de país), cacheada: prompts más cortos, chequeos con reglas y menos cuota.
- **Búsqueda híbrida** keywords + embeddings: mejora el recall de certificaciones y herramientas.
- **Salud de portales:** chequeo diario, aviso si un scraper devuelve 0.
- **Alertas por email semanales** con ofertas nuevas de score alto (retención).
- LinkedIn/Indeed con sesión de usuario: **solo en la versión local**, nunca en producción (ToS).

**Disparador para la Etapa 4:** retención (usuarios que vuelven semana a semana) y pedidos de "más búsquedas" o "alertas diarias".

## Etapa 4 — Monetizar (cuando haya retención)

**Objetivo:** ingresos que paguen la IA y validen el precio.

- **Key propia en tier pago:** el usuario no trae key; sin límite de 500/día; el CV no se usa para entrenar.
  Con eso: evaluación **todo individual** (`RECHECK_TOP = top_n`) y más ofertas evaluadas.
- **Freemium:** X búsquedas gratis por mes; Pro con alertas diarias, más ofertas evaluadas y cartas ilimitadas.
- Política de privacidad y términos; borrar mis datos.

**Disparador para la Etapa 5:** ingresos recurrentes y un techo claro de Streamlit (UX, cuentas, performance).

## Etapa 5 — Escalar el producto (solo con tracción)

- **Frontend propio** (FastAPI + Next.js) si Streamlit limita; el núcleo (`candidate`, `normalize`, `matching`,
  scrapers) se reutiliza tal cual.
- **Ranking aprendido** con el feedback acumulado (miles de interacciones) sobre los factores actuales.
- **Calibración:** que un 80 signifique lo mismo en todas las profesiones, medido con resultados reales
  (entrevistas).

---

## Lo que NO vamos a hacer (por ahora)

Microservicios · migrar el frontend antes de tener usuarios · auto-postulación · app móvil nativa ·
infraestructura paga antes de ingresos · scraping con sesión en producción.

## Costos esperados

| Etapa | Costo mensual |
|---|---|
| 0–3 | ~$0 (free tiers) + dominio (~$12/año) |
| 4 | IA según uso (Gemini flash-lite es barato por llamada) → cubierto por Pro |
| 5 | Hosting propio + IA, solo con ingresos |
