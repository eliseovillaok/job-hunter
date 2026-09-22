# Cómo se puntúa una oferta

El score (0–100) responde una sola pregunta: **¿qué tan bien encaja esta oferta con lo que dice el CV?**
No mide la calidad de la oferta ni de la empresa, y no favorece ningún tipo de empleo: un CV de enfermería,
contabilidad o electricidad se evalúa con las mismas reglas que uno de desarrollo de software.

## Pipeline

| Etapa | Qué hace | ¿Usa IA? | Código |
|---|---|---|---|
| 1. Normalización | Detecta idioma, seniority y modalidad de cada oferta y elimina duplicados entre portales | No | `normalize.py` |
| 2. Filtros duros | Descarta lo que el usuario dijo que no quiere: modalidad, idioma de la oferta, ubicación | No | `matching.apply_hard_filters` |
| 3. Pre-ranking | Ordena por similitud semántica con el perfil (embeddings) y se queda con las N más parecidas | Embeddings | `matching.pre_rank` |
| 4. Evaluación | El LLM puntúa cada **factor** de 0 a 100 y cita la evidencia de la oferta y del CV. Híbrida: lotes para descartar + re-chequeo individual del top (ver abajo) | LLM | `matching.evaluate_hybrid` |
| 5. Score final | El **código** combina los factores con pesos fijos | No | `matching.compute_score` |

Reglas de los filtros: **un dato desconocido nunca descarta una oferta.** Si no se pudo detectar la modalidad o
el idioma, la oferta pasa. La ubicación solo filtra ofertas presenciales o híbridas que declaran una ubicación.

## Factores y pesos

| Factor | Peso | 100 | ~50 | 0 |
|---|---|---|---|---|
| `skills` | 40% | Todos los requisitos centrales aparecen en el CV | La mitad, o solo los secundarios | Ninguno |
| `seniority` | 25% | Mismo nivel / años | Un nivel de distancia (60) · el aviso pide nivel y el CV no lo dice (50) | Dos o más niveles de distancia (20) |
| `role` | 20% | Mismo rol | Rol vecino en el mismo campo | Otro campo |
| `language` | 10% | El CV cubre el idioma requerido | Desconocido o parcial | Falta un idioma requerido |
| `location` | 5% | Compatible o remoto sin restricciones | Información insuficiente | Claramente incompatible |

```
base  = 0.40·skills + 0.25·seniority + 0.20·role + 0.10·language + 0.05·location
score = base × min(1, max(role, skills) / 50)        (redondeado)
```

**Compuerta por rol.** Seniority, idioma y ubicación describen *cómo* encaja una oferta, no *si* es del campo
del candidato. Por eso solo suman en proporción al encaje del trabajo en sí: si `role` o `skills` llega a 50,
la compuerta no reduce nada; si ambos están cerca de 0 (otro campo), el score tiende a 0. Sin la compuerta, en
el eval una jefatura de enfermería sacaba 60 para un supervisor de depósito solo por nivel, idioma y ciudad.

Los pesos viven en `matching.WEIGHTS`. **Cambiarlos requiere aprobación y actualizar este documento.**

## Bandas

| Score | Lectura |
|---|---|
| 80–100 | Encaje fuerte: rol, nivel y requisitos centrales coinciden |
| 60–79 | Encaje sólido con brechas menores |
| 40–59 | Encaje parcial: falta algo importante (nivel o requisitos clave) |
| 0–39 | Encaje débil |

El número es una **estimación de la IA**, no una medición: dos ofertas con 72 y 75 son equivalentes.
Por eso cada score se muestra junto a su desglose por factor y la evidencia citada.

## Hechos vs. inferencias

| Dato | Origen | Cómo se muestra |
|---|---|---|
| Texto de la oferta y del CV | Fuente original | Tal cual |
| Idioma, seniority, modalidad de la oferta | Reglas en `normalize.py` | `unknown` si no hay evidencia clara |
| Perfil estructurado (seniority, años, skills) | IA, con la cita del CV que lo respalda | Editable por el usuario antes de buscar |
| Score por factor, motivos, faltantes | IA | Con la evidencia citada de la oferta y del CV |
| Score final | Código (fórmula de arriba) | Junto al desglose |

## Evaluación híbrida (decisión 2026-09)

**Qué hace.** Las N candidatas (40 por defecto) se evalúan primero **en lotes de 5** (screening) y después las
**10 mejores se re-evalúan de a una**. El resultado individual reemplaza al del lote. Son ~18 llamadas por
búsqueda en lugar de 40.

**Por qué.**
- *Exactitud:* en lote, la IA mezcla información entre ofertas. Medido en el eval: "Sous Chef" para un supervisor
  de depósito sacaba **64 en lote y 0 evaluada sola**. De a una, las ofertas de otro campo quedaron en 0 en todos
  los perfiles.
- *Cuota:* el free tier de Gemini da **500 llamadas por día y por modelo**, más un límite por minuto. Todo de a una
  (40 llamadas) deja ~12 búsquedas diarias por usuario; la híbrida, ~27.
- El usuario mira el top: ahí es donde tiene que ser exacto.

**Límite conocido.** Una oferta que el lote subestime y quede fuera del top 10 no se re-evalúa (falso negativo
posible). El error observado en lotes fue sobre todo *sobreestimar* ofertas ajenas, que el re-chequeo corrige;
hay que confirmarlo con `python -m eval.run --mode hybrid` vs `--mode single`.

**Ritmo.** `ai_engine` espacia las llamadas por key (`GEMINI_RPM`, 15 por defecto) para no chocar con el límite
por minuto; las ráfagas de 429 hacían esperar ~40 s por reintento.

**Cómo mejorarlo (en este orden).**
1. **Caché de evaluaciones** por (oferta, versión del perfil): repetir una búsqueda no gasta cuota.
2. **Extracción de requisitos por oferta, una sola vez** (obligatorios, deseables, años, licencias, idioma):
   prompts más cortos y chequeos con reglas.
3. **Key paga propia** (Fase de monetización): subir `RECHECK_TOP` hasta `top_n` (todo individual) y `GEMINI_RPM`.
4. **Medir y ajustar** `SCREEN_BATCH` / `RECHECK_TOP` con el eval: si el híbrido pierde NDCG frente a
   `single`, bajar el tamaño del lote o subir el re-chequeo.

## Ofertas no evaluadas

Si la IA falla (error, respuesta inválida, cuota agotada o API key inválida), la oferta queda
**"No evaluada"**: no recibe score, no se recomienda y se lista al final. Nunca se la muestra como un match débil.

## Determinismo

La evaluación usa salida JSON con esquema, temperatura 0 y `seed` fijo, para que la misma oferta con el mismo
perfil dé el mismo resultado (el proveedor no lo garantiza al 100%).
