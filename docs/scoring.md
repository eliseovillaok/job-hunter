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
| 4. Evaluación | El LLM puntúa cada **factor** de 0 a 100 y cita la evidencia de la oferta y del CV | LLM | `matching.evaluate` |
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

`score = 0.40·skills + 0.25·seniority + 0.20·role + 0.10·language + 0.05·location` (redondeado).

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

## Ofertas no evaluadas

Si la IA falla (error, respuesta inválida, cuota agotada o API key inválida), la oferta queda
**"No evaluada"**: no recibe score, no se recomienda y se lista al final. Nunca se la muestra como un match débil.

## Determinismo

La evaluación usa salida JSON con esquema, temperatura 0 y `seed` fijo, para que la misma oferta con el mismo
perfil dé el mismo resultado (el proveedor no lo garantiza al 100%).
