---
name: ZENIT | La Esperanza
description: Sistema local de predicción de desabasto e inventario farmacéutico
colors:
  primary: "#1b5e4b"
  primary-hover: "#134638"
  primary-subtle: "#e0f2ec"
  neutral-bg: "#f4f5f0"
  neutral-surface: "#fafbf7"
  neutral-sidebar: "#edf3ee"
  neutral-border: "#cfd7cd"
  neutral-text: "#1e2e26"
  neutral-muted: "#51685d"
  error: "#c93b2b"
  error-bg: "#faecea"
  copilot-bg: "#162822"
  copilot-surface: "#1f372f"
  copilot-text: "#e8ede9"
  copilot-accent: "#72d5b2"
typography:
  display:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: "1.2"
  headline:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: "1.3"
  title:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: "1.4"
  body:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.5"
  label:
    fontFamily: "SF Mono, JetBrains Mono, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 500
    letterSpacing: "0.05em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
---

# Design System: ZENIT | La Esperanza

## 1. Overview

**Creative North Star: "The Frugal Clinical Ledger"**

ZENIT está diseñado como un libro de inventario farmacéutico sobrio, confiable y de alta densidad para una farmacia comunitaria de barrio. Cada decisión visual prioriza la certeza de los datos observados sobre cualquier adorno estético. Rechaza tajantemente la saturación visual, los degradados de neón, los modos oscuros de juguete y las metáforas financieras llamativas.

La interfaz opera como un instrumento clínico: fondo cálido y limpio de papel satinado, contraste de texto carbón-esmeralda de alta legibilidad, y un código semántico firme donde el color rojo se reserva con exclusividad absoluta para alertas de rotura de stock crítica (probabilidad de desabasto $\ge 0.50$ o existencia cero).

**Key Characteristics:**
- **Densidad informativa balanceada:** Grillas tabulares estructuradas con paginación de 20 registros para laptops de farmacia sin pantalla táctil o monitores modestos.
- **Jerarquía Kraljic inconfundible:** Los productos estratégicos y cuellos de botella destacan por su posición y badges sin estridencia.
- **Copiloto Invertido (*Slate Contrast*):** El asistente local se diferencia como un cajón elevado oscuro para no confundir asistencia conversacional con datos tabulares del registro.

## 2. Colors

La paleta se fundamenta en un verde bosque clínico templado sobre neutros cálidos de papel y grises verdosos.

### Primary
- **Clinical Forest Green** (`#1b5e4b` / `oklch(0.43 0.095 155)`): Acción primaria, estado de inferencia completada y acento de marca institucional.
- **Deep Canopy Hover** (`#134638` / `oklch(0.36 0.095 155)`): Estado activo/hover de botones de navegación e interacción.

### Neutral
- **Ledger Cream Canvas** (`#f4f5f0` / `oklch(0.955 0.014 98)`): Fondo principal de la aplicación.
- **Card Surface** (`#fafbf7` / `oklch(0.985 0.008 98)`): Superficie de tablas y paneles.
- **Muted Sage Border** (`#cfd7cd` / `oklch(0.84 0.018 100)`): Líneas divisorias de tablas y marcos.
- **Deep Carbon Ink** (`#1e2e26` / `oklch(0.25 0.025 160)`): Tipografía principal para nombres de medicamentos y existencia.
- **Subtle Muted Pine** (`#51685d` / `oklch(0.43 0.025 160)`): Metadatos, subtítulos y kickers.

### Semántica de Alerta
- **Critical Stock-Out Red** (`#c93b2b` / `oklch(0.51 0.16 27)`): Exclusivo para celdas y badges de desabasto o error grave.
- **Critical Red Background Tint** (`#faecea` / `oklch(0.93 0.035 27)`): Fondo de celdas en peligro crítico.

### Named Rules
**The Critical Red Exclusivity Rule.** Queda estrictamente prohibido usar rojo o magenta en elementos de navegación, etiquetas genéricas o bordes decorativos. El rojo comunica una sola cosa: probabilidad de desabasto inminente o producto en existencia cero.

## 3. Typography

**Display Font:** `Segoe UI`, `-apple-system`, `system-ui`, `sans-serif`  
**Body Font:** `Segoe UI`, `-apple-system`, `system-ui`, `sans-serif`  
**Mono/Numeric Font:** `SF Mono`, `JetBrains Mono`, `Consolas`, `monospace`  

**Character:** Tipografía nativa del sistema operativo para costo cero y rendimiento instantáneo offline, combinada con números monoespaciados para lectura rápida de inventarios y fechas.

### Hierarchy
- **Headline (Pantalla):** Semibold, 1.25rem - 1.5rem, line-height 1.25. Título de la vista actual.
- **Title (Sección/Card):** Semibold, 1rem (16px), line-height 1.4. Encabezados de métricas y filtros.
- **Body (Texto general):** Regular, 0.875rem (14px), line-height 1.5. Explicaciones y descripciones.
- **Table Data (Inventario):** Regular / Medium, 0.8125rem (13px), line-height 1.4. Celdas de 50 productos.
- **Label / Metric (KPIs & Fechas):** Monospace 500, 0.75rem - 1.75rem, tracking 0.05em. Fecha de corte y probabilidades.

## 4. Elevation

El sistema es estrictamente tonal y plano por defecto (*Flat-By-Default*). La profundidad se logra mediante variación de luminosidad entre el fondo (`--color-bg`), la superficie (`--color-surface`) y las divisiones de borde sutil (`--color-border-subtle`).

### Shadow Vocabulary
- **Modal / Copilot Elevated Drawer** (`box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1)`): Utilizado únicamente cuando el copiloto o un diálogo modal se superpone al inventario.

### Named Rules
**The Flat Ledger Rule.** Las tablas, tarjetas de KPI y filas de inventario nunca usan sombras en estado de reposo. La separación visual se realiza por contraste cromático y bordes discretos de 1px.

## 5. Components

### Botones
- **Shape:** Radio moderado (6px / `{rounded.md}`).
- **Primary:** Fondo `{colors.primary}`, texto blanco, padding `8px 16px`. Usado para "Cargar dataset", "Predecir" y "Aprobar orden".
- **Outline / Secondary:** Fondo transparente o blanco, borde de 1px `{colors.neutral-border}`, texto `{colors.neutral-text}`.

### Celdas de Tabla y Badges
- **Cuadrante Kraljic:** Badges redondeados con colores diferenciados:
  - *Estratégico:* Púrpura azulado sobrio.
  - *Cuello de botella:* Ámbar profundo.
  - *Apalancamiento:* Verde azulado neutro.
  - *No crítico:* Gris pizarra.
- **Riesgo TFT:** Si la probabilidad es $\ge 50\%$, la celda aplica fondo `{colors.error-bg}` y texto `{colors.error}` en negrita.

### Copiloto Local (Drawer Invertido)
- Cajón flotante oscuro en esquina inferior derecha (`#162822`), texto claro (`#e8ede9`) y acentos menta (`#72d5b2`). Permite al operador consultar el inventario sin contaminar la vista principal de la tabla.

## 6. Do's and Don'ts

### Do:
- **Do** reservar el color rojo exclusivamente para alertas reales de desabasto ($\ge 0.50$) o existencia cero.
- **Do** indicar explícitamente en la interfaz la diferencia entre la fecha de corte de existencias y la fecha de predicción del modelo.
- **Do** exigir confirmación explícita mediante botón humano para aprobar sugerencias de reabastecimiento.
- **Do** mantener la paginación a 20 registros por vista para optimizar el rendimiento en pantallas de mostradores.

### Don't:
- **Don't** inventar cantidades de compra o precios en la tabla sin una orden explícitamente calculada por las reglas de negocio.
- **Don't** usar degradados de colores llamativos, efectos de vidrio (*glassmorphism*) ni fondos oscuros para la grilla de datos principal.
- **Don't** simular predicciones exitosas ni mostrar datos ficticios cuando el modelo TFT local o el checkpoint fallen; el sistema debe reportar el error real.
- **Don't** utilizar librerías de fuentes web externas que requieran conexión a Internet para renderizar la interfaz.
