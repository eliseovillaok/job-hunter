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

**Oficial: monograma JH de dos tonos** (versión D1). Lámina con todos los usos: [logo-options.html](logo-options.html).
Tipografía del monograma: Bricolage Grotesque 800 (en los archivos finales, convertida a trazos vectoriales).

| Pieza | Cómo es | Dónde |
|---|---|---|
| **Ícono de app / favicon** | Recuadro verde bosque `#13261E`, **J menta `#7FC8A9` + H blanca**. Sin borde ni sombra: el sistema recorta la forma | Tiendas, pantalla de inicio, pestaña del navegador |
| **Logo sobre fondo claro** | Ícono con recuadro + "JobHunter", o JH sin recuadro (J esmeralda `#1F6F54` + H bosque `#13261E`) | Encabezado de la app, documentos |
| **Logo sobre fondo oscuro o de color** | **Siempre JH sin recuadro**: J menta + H blanca (sobre esmeralda: J menta clara `#DDF0E6` + H blanca) | Banners oscuros, modo oscuro, piezas de marketing |

**Archivos oficiales** en [logo/](logo/) (trazos vectoriales, no dependen de fuentes). Vista previa: [logo/preview.html](logo/preview.html).

| Archivo | Uso |
|---|---|
| `icon.svg` · `icon-1024.png` · `icon-512.png` | Ícono de app cuadrado (las tiendas aplican su máscara) |
| `icon-rounded.svg` · `favicon-32.png` · `favicon-16.png` · `apple-touch-icon.png` | Web: favicon y acceso directo |
| `lockup-light.svg` | Ícono + nombre, fondo claro (principal) |
| `lockup-light-glyph.svg` | JH sin recuadro + nombre, fondo claro liviano |
| `lockup-dark.svg` | JH sin recuadro + nombre, fondo oscuro |
| `glyph-on-light.svg` · `glyph-on-dark.svg` · `glyph-on-emerald.svg` · `glyph-mono.svg` | Solo la JH, según el fondo; mono usa `currentColor` |

Se regeneran con `python scripts/build_logo.py <BricolageGrotesque.ttf>` (fuente OFL, no se versiona; ver el script).
**No editar los SVG a mano**: cambiar el script y regenerar.

Reglas:
- **Nunca** poner el recuadro verde bosque sobre fondos casi negros: ahí se usa la JH sin recuadro.
- En los lockups, la JH sin recuadro tiene **el mismo tamaño y posición** que dentro del recuadro: al cambiar de tema solo desaparece el fondo, las letras no crecen ni el nombre se mueve.
- Área de respeto: la mitad del alto del isotipo alrededor de todo el logo.
- Tamaño mínimo: ícono 16 px (favicon); ícono + nombre, 100 px de ancho.
- No: bordes, sombras, degradados, rotar, deformar, cambiar colores fuera de los tokens, poner el logo sobre fotos sin fondo.

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
| Borde de control | `#77917F` | `#5A7A69` | Botones, campos, chips e interruptores. **Obligatorio ≥ 3:1**: los bordes decorativos de tarjetas usan `border` |
| Éxito · Aviso · Error · Info | `#377227` · `#8F5D00` · `#B42318` · `#2B5C8A` | `#8BCB6F` · `#F0B955` · `#F28B7F` · `#8CB8E6` | Estados. El éxito es verde hoja, distinto del primario |

**Proporción aproximada:** 60% fondos claros · 25% texto y superficies · 10% esmeralda · 5% coral.
Un solo acento cálido por pantalla. El coral no compite con el botón primario.

**Accesibilidad (obligatorio):** texto ≥ 4.5:1 (texto principal ≥ 7:1), botones y estados ≥ 4.5:1, en claro y oscuro.
El **contorno de cualquier control** (botón, campo, chip, interruptor) ≥ 3:1 contra su fondo: si no se distingue, no existe.
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
- **Uso del ancho (evitar el sobrescroll):** no apilar todo en una columna. Campos, datos o textos relacionados van lado a lado (2–3 columnas) cuando el ancho lo permite; en móvil se apilan. Sin compactar: se mantienen los espaciados y tamaños de arriba, lo que se ahorra son renglones, no aire.
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

### Movimiento e interacción

El producto se siente fluido y predecible. Estas reglas aplican a toda pantalla nueva, sin que haga falta pedirlas:

- **Nunca recargar la página entera** dentro de la app: navegación, idioma y formularios reemplazan el contenido con una transición (sin parpadeo). El cambio de tema es un fundido.
- **Duraciones:** 150–320 ms. Entradas con `cubic-bezier(.2,.7,.2,1)`; salidas más cortas que las entradas. Nada de rebotes largos.
- **Todo lo que se abre o cierra se anima** (paneles, grupos, opciones avanzadas, tooltips): altura + opacidad. Nada aparece o desaparece de golpe.
- **Scroll suave** en enlaces internos y botón circular **Volver arriba** (abajo a la derecha) cuando la página es larga.
- **Cada acción tiene respuesta inmediata:** hover, foco visible, presión (escala .97), estados "subiendo…", "verificando…", "analizando…", y el botón no se puede presionar dos veces.
- **Guiar sin sobrecargar:** un solo botón principal por pantalla; se habilita (con un pulso breve) cuando lo necesario está completo y un texto al lado dice qué falta. Las aclaraciones secundarias van en tooltips ⓘ (hover, teclado o toque), no en renglones fijos.
- **Sin scroll innecesario:** una pantalla corta debe entrar entera en una laptop (1366×657 útiles).
- **Estado consistente:** lo que se ve es lo que guardó el servidor. Lo escrito se guarda solo mientras se edita (cambiar de idioma, recargar o volver atrás no pierde nada) y los datos secretos se muestran enmascarados (`AIza…a1b2`).
- **Accesibilidad:** con `prefers-reduced-motion` se desactivan las animaciones.

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

**Registro: cercano, no coloquial.** Tuteo sí, charla informal no. Nada de muletillas ni expresiones de un país.

| Sí | No |
|---|---|
| "Tiempo restante estimado: 1 min 10 s" | "Faltan unos 70 segundos" |
| "Los resultados aparecerán en cuanto termine la búsqueda." | "Te los mostramos apenas terminemos." |
| "Pégala en este campo." | "Pégala aquí. ¡Listo!" |
| "alrededor de 3 minutos", "~3 min" | "unos 3 minutos" |
| "Selecciona…" | "Toca…", "Dale a…" |

| Sí | No |
|---|---|
| "Te mostramos por qué cada oferta coincide con tu experiencia." | "¡Nuestra IA mágica encuentra tu trabajo soñado!" |
| "Tu CV no indica tu nivel: lo dejamos como no especificado." | Inventar o suponer datos del usuario |
| "No pudimos evaluar esta oferta." | "Error 500" o mensajes técnicos |
| Cifras reales del producto (13 portales, 12 profesiones en el test) | Métricas o testimonios inventados |

**Vocabulario del producto**

| Usar | Evitar |
|---|---|
| afinidad, coincide, se ajusta a tu perfil | encaja, matchea, match (en ES) |
| oferta, puesto, empleo, vacante | laburo, curro, chamba |
| perfil, CV | currículum vitae (salvo en texto legal) |
| en inglés: **resume** (en español: **CV**) | "CV" en la copy en inglés |
| portales de empleo | job boards (en ES) |
| explicación, por qué | "insights" |

**La IA:** se menciona cuando aporta claridad ("la IA estima…"), nunca como promesa mágica. Siempre dejar claro qué es
un dato del CV o de la oferta y qué es una estimación.

**Inglés:** mismo tono; "match" sí es natural en inglés (Strong match). Capitalización tipo oración en botones y títulos.

## 9. Checklist antes de cada cambio

- [ ] Colores solo de `tokens.json`; contraste verificado en claro y oscuro.
- [ ] Tipografías y pesos de la sección 5.
- [ ] Componentes reutilizados (botón, chip, tarjeta, anillo) antes que crear nuevos.
- [ ] Movimiento e interacción (§6): transiciones, estados de carga, tooltips, sin recargas ni scroll innecesario, estado consistente.
- [ ] Texto en español neutro (tú, sin voseo ni regionalismos) y su versión en inglés.
- [ ] Vocabulario del producto (afinidad, oferta, perfil).
- [ ] Sin datos inventados (usuarios, métricas, testimonios).
- [ ] Probado en escritorio y en celular.
