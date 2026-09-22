# Manual de marca — JobHunter

**Antes de cualquier cambio visual o de texto, revisar este manual.** Si un cambio no cumple estas reglas,
se propone un cambio al manual (con su motivo) antes de implementarlo; nunca se improvisa en el código.

Referencias vivas:
[paleta](palette.svg) · [tokens](tokens.json) · [opciones de logotipo](logo-options.html) · [maqueta v1](../design/mockup-v1.html)

---

## 1. Esencia

| | |
|---|---|
| **Qué somos** | Una herramienta que busca empleo en muchos portales a partir de tu CV y explica por qué cada oferta coincide contigo. |
| **Para quién** | Personas de **cualquier profesión** en Latinoamérica, España/Europa y EE. UU. No solo perfiles tech. |
| **Promesa** | Menos tiempo buscando, más claridad sobre qué ofertas valen la pena. |
| **Diferencial** | Transparencia (cada puntaje con su porqué), honestidad (no inflamos el perfil), el mismo criterio para todas las profesiones. |

**Valores de marca → cómo se ven**

| Valor | Se expresa con |
|---|---|
| Crecimiento | Verde menta, formas que suben, lenguaje de avance |
| Estabilidad | Esmeralda profundo y verde bosque, tipografía firme, layouts ordenados |
| Bienestar | Fondos claros y aireados, espacios generosos, tono calmo |
| Calidez humana | Un solo acento coral, íconos de oficios y profesiones, trato cercano |

## 2. Nombre

- Se escribe **JobHunter**: una palabra, J y H mayúsculas. Nunca "jobhunter", "Job Hunter" ni "JOBHUNTER" (salvo titulares en mayúsculas).
- En el logotipo, "Job" va en el color de texto y "Hunter" en el primario.
- No traducir el nombre.

## 3. Logotipo

Estado: **pendiente de elección** entre las opciones de [logo-options.html](logo-options.html).
Mientras tanto se usa la opción **D** (bloque esmeralda + punto coral), la de la maqueta.

Reglas (aplican a la opción elegida):
- Área de respeto: la mitad del alto del isotipo alrededor de todo el logo.
- Tamaño mínimo: isotipo 16 px (favicon); isotipo + nombre, 100 px de ancho.
- Versiones: claro (sobre `bg`/`surface`), oscuro (sobre `dark.bg`), monocromo (un solo color de texto).
- No: deformar, rotar, agregar sombras o degradados, cambiar colores fuera de los tokens, poner el logo sobre fotos sin fondo.

## 4. Color

Fuente de verdad: [tokens.json](tokens.json). **No inventar colores**: si falta uno, se agrega al JSON verificando el contraste.

| Rol | Claro | Oscuro | Uso |
|---|---|---|---|
| Primario | `#1F6F54` | `#5FCB9F` | Botones principales, enlaces, marca |
| Primario hover | `#185A44` | `#7AD6B0` | Hover, títulos destacados |
| Secundario (menta) | `#7FC8A9` | `#3E8E6E` | Ilustración y gráficos. **Nunca para texto** en claro |
| Superficie destacada | `#DDF0E6` | `#1E3129` | Chips, badges de puntaje, destacados |
| Fondo / superficie | `#F4F8F5` / `#FFFFFF` | `#0F1A16` / `#16241E` | Página / tarjetas |
| Texto / secundario / atenuado | `#13261E` / `#3E5A4E` / `#58736A` | `#E8F2EC` / `#A9C2B6` / `#8FA79B` | Jerarquía de texto |
| Acento coral | `#E07A5F` | `#F29A80` | Decoración, novedades. Con texto blanco usar `#A8472E` |
| Éxito · Aviso · Error · Info | `#377227` · `#8F5D00` · `#B42318` · `#2B5C8A` | `#8BCB6F` · `#F0B955` · `#F28B7F` · `#8CB8E6` | Estados. El éxito es verde hoja, distinto del primario |

**Proporción aproximada:** 60% fondos claros · 25% texto y superficies · 10% esmeralda · 5% coral.
Un solo acento cálido por pantalla. El coral no compite con el botón primario.

**Accesibilidad (obligatorio):** texto ≥ 4.5:1 (texto principal ≥ 7:1), botones y estados ≥ 4.5:1, en claro y oscuro.
Nunca comunicar algo solo con color (ej.: el puntaje lleva número y etiqueta, no solo el anillo).

## 5. Tipografía

| Uso | Fuente | Peso | Notas |
|---|---|---|---|
| Titulares de marca (hero) | Bricolage Grotesque | 800 | MAYÚSCULAS, interlineado 0.98, tracking −3% |
| Títulos de sección y tarjeta | Bricolage Grotesque | 700–800 | Oración (sin mayúsculas forzadas) |
| Texto, UI, formularios | Inter | 400–700 | 14–17 px en cuerpo |
| Etiquetas / eyebrows | Inter | 600–700 | 12 px, MAYÚSCULAS, tracking +8% |

Ambas gratuitas (Google Fonts). No mezclar una tercera familia.

## 6. Forma, espacio y componentes

- **Radios:** tarjetas 22 px · bloques grandes (hero, franja) 28 px · botones, chips y campos: píldora (999 px) · isotipo 10–16 px.
- **Espaciado:** base de 4 px; separación entre secciones 48–56 px; padding de tarjetas 22–26 px.
- **Sombras:** mínimas. Tarjetas planas con borde `border`; sombra suave solo en hover.
- **Botones:** primario (fondo esmeralda, texto blanco) · secundario (borde esmeralda, fondo superficie) · terciario (texto). Uno solo primario por grupo.
- **Chips:** filtros y atributos (modalidad, nivel). Activo = superficie destacada + texto primario.
- **Tarjeta de oferta:** avatar con inicial de la empresa · título · empresa, ubicación y portal · chips · motivos (✓, color éxito) y faltantes (•, color aviso) visibles sin abrir nada · acciones · anillo de afinidad a la derecha.
- **Afinidad (puntaje):** anillo + número + etiqueta. Bandas de [docs/scoring.md](../scoring.md):

  | Puntaje | Etiqueta ES | Etiqueta EN | Color del anillo |
  |---|---|---|---|
  | 80–100 | Afinidad alta | Strong match | Primario |
  | 60–79 | Afinidad buena | Good match | `#C98A1A` (ámbar) |
  | 40–59 | Afinidad parcial | Partial match | Atenuado |
  | 0–39 | Afinidad baja | Low match | Atenuado |

## 7. Iconografía e ilustración

- Íconos de línea, trazo 2 px (6 en ilustraciones grandes), extremos redondeados, un color.
- Ilustración = **mosaico geométrico**: bloques de color de la paleta con íconos de profesiones (salud, oficios, oficina,
  educación, gastronomía…) y formas simples (círculo, rombo, ondas). Representa que el producto es para **cualquier profesión**.
- Sin fotos de stock por ahora. Si se usan en el futuro: personas reales y diversas, luz natural, sin poses corporativas.
- Emojis: solo como apoyo puntual en la interfaz, nunca como íconos de marca.

## 8. Voz y tono

**Idioma:** español **neutro internacional** (LATAM, España, EE. UU.) e inglés.
- Tratamiento de **tú** (Sube, Revisa, Encuentra). **Nunca** voseo (Subí, Revisá, vos) ni regionalismos de un país.
- Evitar "ustedes/vosotros" y modismos locales. Vocabulario comprensible en todos los mercados.

**Personalidad:** clara, honesta, cercana, profesional. Como alguien experto que te ayuda, no como un vendedor.

| Sí | No |
|---|---|
| "Te mostramos por qué cada oferta coincide con tu experiencia." | "¡Nuestra IA mágica encuentra tu trabajo soñado!" |
| "Tu CV no indica tu nivel: lo dejamos como no especificado." | Inventar o suponer datos del usuario |
| "No pudimos evaluar esta oferta." | "Error 500" o mensajes técnicos |
| Cifras reales del producto (19 portales, 12 profesiones en el test) | Métricas o testimonios inventados |

**Vocabulario del producto**

| Usar | Evitar |
|---|---|
| afinidad, coincide, se ajusta a tu perfil | encaja, matchea, match (en ES) |
| oferta, puesto, empleo, vacante | laburo, curro, chamba |
| perfil, CV | currículum vitae (salvo en texto legal) |
| portales de empleo | job boards (en ES) |
| explicación, por qué | "insights" |

**La IA:** se menciona cuando aporta claridad ("la IA estima…"), nunca como promesa mágica. Siempre dejar claro qué es
un dato del CV o de la oferta y qué es una estimación.

**Inglés:** mismo tono; "match" sí es natural en inglés (Strong match). Capitalización tipo oración en botones y títulos.

## 9. Checklist antes de cada cambio

- [ ] Colores solo de `tokens.json`; contraste verificado en claro y oscuro.
- [ ] Tipografías y pesos de la sección 5.
- [ ] Componentes reutilizados (botón, chip, tarjeta, anillo) antes que crear nuevos.
- [ ] Texto en español neutro (tú, sin voseo ni regionalismos) y su versión en inglés.
- [ ] Vocabulario del producto (afinidad, oferta, perfil).
- [ ] Sin datos inventados (usuarios, métricas, testimonios).
- [ ] Probado en escritorio y en celular.
