# Índice de Documentación: ZENIT (Estructura Diátaxis)

Bienvenido a la base de conocimiento de **ZENIT**. Toda la documentación ha sido reestructurada aplicando el estándar **Diátaxis** (orientado a claridad técnica y consumo tanto por desarrolladores humanos como por agentes de IA) junto con el marco **Impeccable** de diseño y producto.

---

## 🧭 Los Cuatro Cuadrantes Diátaxis

```
                      APRENDIZAJE (Práctica)
                                ▲
                                │
        TUTORIALES              │             CÓMO HACER (How-To)
  (Guiar paso a paso)           │             (Resolver problemas)
                                │
  • guias/INSTRUCCIONES_ZENIT.md│  • guias/Alcance_logrado.md
                                │  • producto/propuestas.md
────────────────────────────────┼─────────────────────────────────► INFORMACIÓN (Teoría)
                                │
       EXPLICACIÓN              │                 REFERENCIA
     (Entender conceptos)       │             (Máquinas y Tokens)
                                │
  • especificaciones/           │  • diseno/DESIGN_SYSTEM.md
    01_CONTEXTO_ZENITH.md       │  • especificaciones/
    04_SECCION_2_ARQUITECTURA...│    02_RESTRICCIONES_SECCION_1.md
  • producto/PRODUCT.md         │  • analisis_openjarvis/
                                │
                                ▼
                       CONOCIMIENTO (Profundo)
```

---

## 📂 Directorio de Documentos

### 1. `diseno/` (Design System & Tokens)
- **[DESIGN_SYSTEM.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/diseno/DESIGN_SYSTEM.md)** `[Referencia]`:  
  Tokens computables (formato Stitch YAML + Markdown), paleta cromática clínica en espacio **OKLCH**, reglas de elevación plana, componentes y la regla estricta de exclusividad del color rojo para desabasto.

### 2. `producto/` (Estrategia, IA y Reglas de Negocio)
- **[PRODUCT.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/producto/PRODUCT.md)** `[Explicación]`:  
  Propósito del producto, usuario arquetípico (dueño de la farmacia "La Esperanza"), principios estratégicos y anti-referencias visuales.
- **[propuestas.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/producto/propuestas.md)** `[How-To / Arquitectura de IA]`:  
  Capacidades operativas del asistente conversacional (Gemini, GPT o local), orquestación con el modelo predictivo TFT y **guardrails de seguridad obligatorios** para evitar cualquier alteración destructiva en la base de datos o exposición de datos sensibles.

### 3. `guias/` (Tutoriales y Estado de Implementación)
- **[INSTRUCCIONES_ZENIT.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/guias/INSTRUCCIONES_ZENIT.md)** `[Tutorial / Receta rápida]`:  
  Flujo paso a paso con comandos reproducibles para inicializar datos, entrenar el TFT en CPU, ejecutar pruebas con `pytest` y levantar la API FastAPI y el frontend de Vite.
- **[Alcance_logrado.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/guias/Alcance_logrado.md)** `[How-To / Diagnóstico]`:  
  Estado de avance técnico verificado con evidencia (tiempos de inferencia, métricas F1 y funcionalidades validadas vs. pendientes).

### 4. `especificaciones/` (Fundamentos Metodológicos del Prototipo)
- **[01_CONTEXTO_ZENITH.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/especificaciones/01_CONTEXTO_ZENITH.md)** `[Explicación]`:  
  El problema real de las farmacias comunitarias, la lógica de la Matriz de Kraljic y la arquitectura de percepción-razonamiento-acción.
- **[02_RESTRICCIONES_SECCION_1.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/especificaciones/02_RESTRICCIONES_SECCION_1.md)** `[Referencia]`:  
  Reglas del universo cerrado canónico (50 productos, 90 días, 4,500 filas, 8 columnas).
- **[03_PLAN_DE_ARMADO.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/especificaciones/03_PLAN_DE_ARMADO.md)** `[How-To]`:  
  Plan de ingeniería paso a paso para el ensamblado del prototipo.
- **[04_SECCION_2_ARQUITECTURA_FRUGAL.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/especificaciones/04_SECCION_2_ARQUITECTURA_FRUGAL.md)** `[Explicación]`:  
  Justificación de costo 0.00 MXN mediante software libre y CPU local.
- **[05_SECCION_3_HITOS_VALIDACION.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/especificaciones/05_SECCION_3_HITOS_VALIDACION.md)** `[Referencia]`:  
  Criterios de éxito formal y registro histórico de pruebas.

### 5. `analisis_openjarvis/` (Auditoría del Código Base)
- **[JARBIS_INVENTARIO.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/analisis_openjarvis/JARBIS_INVENTARIO.md)** y **[New_data_info.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/analisis_openjarvis/New_data_info.md)** `[Referencia]`:  
  Auditoría profunda de la arquitectura heredada de OpenJarvis y sus primitivas.
