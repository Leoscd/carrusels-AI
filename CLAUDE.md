# CLAUDE.md — Soy Leo AI / Carruseles Instagram

## Proyecto
Carruseles de Instagram para **@soy.leo_ai** — arquitecto consultor de IA en Tucumán, Argentina.
Audiencia: arquitectos y estudios que quieren incorporar IA a su flujo de trabajo.

## Estructura del proyecto

```
abril/
├── app/                        React + Vite — generador web de carruseles
├── carrusel_templates.html     Biblioteca de 6 layouts brutalistas (referencia)
├── carrusel_03_cowork.html     Carrusel: cowork con Claude (6 slides)
├── carrusel_06_auditoria.html  Carrusel: auditoría normativa de planos (6 slides)
├── carrusel_1/2/3/4.html       Carruseles viejos (estilo gold/luxury — pendientes migrar)
└── referencias para carrusel/  Imágenes de referencia visual (1.jpg–5.jpg)
```

Cada HTML de carrusel es **autónomo**: fonts vía Google CDN, html2canvas vía CDN, sin build.

## Cómo funciona cada carrusel HTML

- Slides: divs `.slide` de **1080×1350px** apilados en `.carousel-container`
- Botón "Descargar todos" → `downloadAll()` con html2canvas
- Nombre de descarga: `carrusel_XXX_slide_NN.png`
- `html2canvas` backgroundColor: `'#EB4604'` si CTA slide, `'#171614'` para el resto

---

## Sistema de diseño brutalista (OBLIGATORIO en todo carrusel nuevo)

### Paleta de marca

```css
--night:        #171614   /* fondo base */
--smoky:        #100C0B   /* fondo alternativo */
--eerie-black:  #1C1B17   /* superficies */
--eerie-light:  #282723   /* bordes / separadores */
--hot-orange:   #EB4604   /* acento primario — headlines, CTAs, bordes activos */
--orange-wheel: #F77E0D   /* acento secundario */
--moss:         #99A57D   /* labels, handles, texto terciario */
--white:        #FFFFFF   /* texto primario */
--cream:        #F5F0E8   /* texto secundario */
```

### Tipografía

Google Fonts: `Barlow Condensed:wght@400;700;800;900` + `Inter:wght@400;700;900`

| Uso | Fuente | Peso | Estilo |
|-----|--------|------|--------|
| H1 / títulos grandes | Barlow Condensed | 900 | ALL CAPS, letter-spacing -2px, line-height 0.88 |
| Labels / pasos | Barlow Condensed | 700 | uppercase, letter-spacing 4px, color --moss |
| Body | Inter | 400 | 34–40px |
| Stats / números grandes | Barlow Condensed | 900 | 160–200px, color --hot-orange |

### Reglas brutalistas (sin excepciones)

1. **CERO** gradientes, glows, glass effects, box-shadow decorativos
2. Solo bordes duros: `3–4px solid`
3. Bloques de color sólidos (sin `rgba` decorativos)
4. Tipografía como elemento gráfico principal
5. Reglas horizontales fuertes (`border-top/bottom: 3–4px solid`)
6. **Sin imágenes** (`<img>` ni `background-image` externas)

---

## Componentes estándar

### Header de slide
```
número del slide → Barlow 700, --moss
línea → border-bottom 3px solid --hot-orange, full-width
```

### Footer de slide
```
border-top: 3px solid --hot-orange
@soy.leo_ai → Barlow 700, --moss
número de slide → Barlow 700, --white
```

### Lista numerada
```
01 / 02 / 03 → --hot-orange
separadores → border-bottom: 1px solid --eerie-light
```

### Step list
```
"PASO 0X" → Barlow 700, --moss, letter-spacing 4px
texto → Barlow 800
border-left: 4px solid --hot-orange
```

### Label-tag
```css
display: inline-block;
background: var(--hot-orange);
color: var(--night);
font-family: 'Barlow Condensed', sans-serif;
font-weight: 900;
transform: rotate(-1.5deg);
```

### CTA slide (siempre el último)
```css
background: #EB4604;   /* full orange */
color: var(--night);
```

---

## Layouts disponibles (ver carrusel_templates.html)

1. **Columnas verticales** — 3 cols night/hot-orange/cream, texto `writing-mode: vertical-rl`
2. **Portada estándar** — H1 grande, label-tag rotado, kicker en moss
3. **Lista numerada** — 01/02/03 en hot-orange con separadores
4. **Stat/número grande** — cifras 180px en hot-orange + HR 3px
5. **Paso a paso** — border-left 4px naranja, PASO label en moss
6. **CTA full orange** — fondo #EB4604, texto en --night

---

## Convenciones al crear un carrusel nuevo

1. Leer `carrusel_templates.html` para elegir layouts
2. Siempre el último slide es CTA full orange
3. Nombre de archivo: `carrusel_NN_tema.html` (ej: `carrusel_07_renders.html`)
4. No agregar imágenes externas
5. No usar el estilo viejo (gold/luxury): si migrás un carrusel viejo, reescribir el CSS completo
