# Propuestas de Diseño UI: Chat e Interfaces de Asistencia con IA para ZENIT

Documento de especificación visual, flujos de interacción y propuestas de interfaz para la integración de capacidades conversacionales inteligentes dentro de la plataforma **ZENIT | Farmacia La Esperanza**, alineado con la filosofía de diseño **"The Frugal Clinical Ledger"** ([DESIGN_SYSTEM.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/diseno/DESIGN_SYSTEM.md)) y los guardrails operativos ([propuestas.md](file:///c:/dev/projects/Zenith-Openjarvis/docs/producto/propuestas.md)).

---

## 1. Fundamentos y Reglas de Diseño

Para preservar la sobriedad clínica de una farmacia comunitaria de barrio, el diseño del chat de IA no debe emular un "chatbot genérico de soporte", sino un **Copiloto Clínico de Inventario**:
1. **Frugalidad Visual:** Sin burbujas de colores estridentes ni avatares distractores. Tipografía legible (`Segoe UI`, datos en monoespaciada `SF Mono`/`JetBrains Mono`).
2. **Slate Contrast (Cajón de Contraste Invertido):** El área conversacional utiliza un tono oscuro profundo (`#162822` / `#1f372f`) para diferenciarse inmediatamente del libro contable tabular claro (`#fafbf7`), evitando confusiones entre datos definitivos y sugerencias preliminares.
3. **Guardrails Semánticos:**
   - Color rojo (`#c93b2b`) reservado **únicamente** para riesgo crítico de desabasto ($\ge 0.50$ o existencia 0).
   - Cualquier acción propuesta por la IA (generar sugerencia de orden, cambiar parámetros) requiere **botón de confirmación explícita** (*Human-in-the-Loop*).
   - Respuestas con badges claros de origen: `[DATOS LOCALES: SQLITE]` o `[INFERENCIA: TFT LOCAL]`.

---

## 2. Propuestas de Interfaces de Chat

A continuación se detallan tres propuestas arquitectónicas de interfaz:

```
+--------------------------------------------------------------------------------------------------+
| PROPUESTA 1: Copiloto Lateral Plegable (Drawer Integrado)                                       |
| -> Flujo sin perder de vista la tabla principal. Perfecto para monitores de laptop de farmacia.  |
+--------------------------------------------------------------------------------------------------+
| PROPUESTA 2: Centro de Mando Conversacional (Dedicated Full-Page Assistant)                     |
| -> Espacio amplio para análisis profundo, simulaciones de reorden y explicabilidad del TFT.      |
+--------------------------------------------------------------------------------------------------+
| PROPUESTA 3: Asistente Contextual Modal / Split Rápido (En Punto de Decisión)                  |
| -> Se abre directamente desde un producto o una orden pendiente con contexto precargado.       |
+--------------------------------------------------------------------------------------------------+
```

---

### Propuesta 1: Copiloto Lateral Plegable (Drawer Clínico)

> **Ideal para:** Monitoreo diario mientras el encargado navega el inventario o la tabla de predicciones.

#### Mockup de Estructura Visual:

```
┌─────────────────────────────────────────────────────────────┬────────────────────────────────────┐
│  ZENIT | Farmacia La Esperanza        [2026-10-22] [Corte]  │  COPILOTO LOCAL ZENIT          [X] │
├─────────────────────────────────────────────────────────────┼────────────────────────────────────┤
│  [Dashboard]  [Inventario (50)]  [Sugerencias (3)]          │  ● Estado: Motor TFT Listo (Local) │
├─────────────────────────────────────────────────────────────┤                                    │
│  Inventario General (Filtro: Todos)                         │  [Usuario]                         │
│  ┌───────────────────────┬─────────┬──────────────┬───────┐ │  "¿Cuáles medicamentos tienen       │
│  │ Producto              │ Exist.  │ Riesgo 7d    │ Kral. │ │   riesgo crítico para mañana?"     │
│  ├───────────────────────┼─────────┼──────────────┼───────┤ │                                    │
│  │ Paracetamol 500mg     │ 14 uds  │ 12% (Bajo)   │ NoCrí │ │  [Copiloto AI]                     │
│  │ Amoxicilina 500mg     │ 2 uds   │ 88% CRÍTICO  │ Estrat│ │  Identifiqué 3 productos en        │
│  │ Insulina NPH 100UI    │ 0 uds   │ 100% AGOTADO │ Cuello│ │  cuadrante crítico:                │
│  │ Losartán 50mg         │ 45 uds  │ 4% (Bajo)    │ Apal  │ │                                    │
│  └───────────────────────┴─────────┴──────────────┴───────┘ │  1. Insulina NPH (0 uds / Cuello)  │
│                                                             │  2. Amoxicilina 500mg (2 uds)      │
│  Paginación: < [1] 2 3 >                                    │                                    │
│                                                             │  ┌───────────────────────────────┐ │
│                                                             │  │ [Acción Sugerida]             │ │
│                                                             │  │ Crear sugerencia de reorden   │ │
│                                                             │  │ [Ver en Sugerencias] [Aprobar]│ │
│                                                             │  └───────────────────────────────┘ │
│                                                             │                                    │
│                                                             │  [ Preguntar a Zenit...      ] [>] │
└─────────────────────────────────────────────────────────────┴────────────────────────────────────┘
```

#### Elementos Clave:
- **Anchura fija:** 380px, acoplado a la derecha, con botón de colapsar `[X]` o tecla rápida `Esc`.
- **Chips de interacción rápida:** *"Ver críticos"*, *"Generar corte canónico"*, *"Calcular órdenes sugeridas"*.
- **Tarjetas de acción incrustadas en el chat:** Los mensajes del modelo renderizan directamente botones para filtrar la tabla izquierda o abrir la ficha del producto.

---

### Propuesta 2: Centro de Mando Conversacional (Full-Page Studio)

> **Ideal para:** Auditorías de inventario, simulaciones de reabastecimiento y análisis de escenarios con el modelo TFT.

#### Mockup de Estructura Visual:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ZENIT > Asistente Inteligente & Auditoría                                 [Descargar Bitácora] │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  HISTORIAL & CONVERSACIONES                    │  DIÁLOGO DE AUDITORÍA & PREDICCIÓN              │
│                                                │                                                 │
│  + Nueva Consulta                              │  [ZENIT AI] 10:14 AM                            │
│  ────────────────────────                      │  Inferencia completada en 18ms (TFT local).     │
│  • Análisis corte semanal 22-Oct               │  Dataset canónico: 4,500 registros evaluados.   │
│  • Revisión cadena de frío (Insulina)          │                                                 │
│  • Validación cuadrantes Kraljic               │  ┌───────────────────────────────────────────┐  │
│                                                │  │ RESUMEN EJECUTIVO                         │  │
│  ESTADO DEL SISTEMA                            │  │ • 4 productos con riesgo ≥ 50%            │  │
│  • Modelo: TFT (PyTorch CPU, h=16)             │  │ • 2 requieren refrigeración (cadena frío) │  │
│  • Datos: 50 productos / Semilla 42            │  │ • Inversión estimada sugerida: $1,240 MXN │  │
│  • Red: 100% Desconectado / Local              │  └───────────────────────────────────────────┘  │
│                                                │                                                 │
│                                                │  [Usuario]                                      │
│                                                │  "Simula el impacto de no surtir Amoxicilina"   │
│                                                │                                                 │
│                                                │  [ZENIT AI]                                     │
│                                                │  Amoxicilina está en el cuadrante ESTRATÉGICO.  │
│                                                │  La rotura afectará el 14% de las recetas de    │
│                                                │  antibióticos proyectadas para el fin de semana.│
│                                                ├─────────────────────────────────────────────────┤
│                                                │  [ Ingrese comando o consulta...          ] [↑] │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```

#### Elementos Clave:
- Panel izquierdo con bitácora de auditorías previas y telemetría de inferencia en milisegundos.
- Explicabilidad del algoritmo: visualización de pesos de atención del TFT y desglose Kraljic.

---

### Propuesta 3: Asistente Contextual en Punto de Decisión (Inline & Modal)

> **Ideal para:** La pantalla de **Sugerencias de Compra**, asistiendo al usuario en el momento exacto de aprobar o rechazar una orden.

#### Mockup de Estructura Visual:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  SUGERENCIAS DE REABASTECIMIENTO (Pendientes de Aprobación)                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│  Orden #104: Amoxicilina 500mg Capsulas                                                          │
│  Prioridad: ALTA (Estratégico)  |  Riesgo 7d: 88%  |  Existencia actual: 2 uds                   │
│                                                                                                  │
│  ┌─ ASISTENTE ZENIT (Evaluación de Decisión) ──────────────────────────────────────────────────┐ │
│  │ 💡 Criterio del modelo: Consumo promedio 4.2 uds/día. Con 2 unidades en anaquel,             │ │
│  │    la probabilidad de quiebre en las próximas 48h es del 91%.                               │ │
│  │                                                                                             │ │
│  │    Cantidad sugerida: [ 30 ] uds (Cubre 7 días + colchón de seguridad)                     │ │
│  │    Costo unitario ref: $45.00  |  Costo estimado total: $1,350.00                           │ │
│  │                                                                                             │ │
│  │    [✓ Aprobar Sugerencia]       [✎ Modificar Cantidad]       [✕ Descartar Orden]            │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                  │
│  Orden #105: Paracetamol Gotas 100mg/ml                                                          │
│  Prioridad: MEDIA (Apalancamiento) | Riesgo 7d: 52% | Existencia actual: 5 uds                   │
│  [Consultar con Copiloto...]                                                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Guía de Componentes y Tokens de Diseño

| Componente | Token / Clase | Especificación Visual |
| :--- | :--- | :--- |
| **Drawer Contenedor** | `zenit-copilot-drawer` | Fondo `#162822`, borde izquierdo `1px solid #1f372f`, ancho `380px`. |
| **Burbuja Usuario** | `zenit-chat-user` | Fondo `#1f372f`, texto `#e8ede9`, radio `8px`, margen izquierdo auto. |
| **Burbuja Asistente**| `zenit-chat-ai` | Fondo `#192e27`, texto `#e8ede9`, borde `1px solid #28473c`. |
| **Badge de Evidencia** | `zenit-badge-evidence`| Fondo `#11201b`, texto `#72d5b2`, tipografía monoespaciada `11px`. |
| **Alerta Crítica** | `zenit-chat-alert` | Fondo `#faecea`, borde `#c93b2b`, texto `#8a1f14` (alto contraste). |
| **Botón de Acción** | `button-primary` | Fondo `#1b5e4b`, hover `#134638`, texto blanco `#ffffff`, radio `6px`. |

---

## 4. Estado de Conexión del MCP Pencil

- **Servidor MCP Pencil configurado:** [mcp.json](file:///c:/dev/projects/Zenith-Openjarvis/mcp.json) apunta a `C:\Users\fitch\AppData\Local\Programs\Pencil\resources\app.asar.unpacked\out\mcp-server-windows-x64.exe --app desktop`.
- **Modo interactivo Pencil:** El servidor MCP de Pencil requiere que la aplicación de escritorio (`Pen.exe`) esté abierta con un documento `.pen` activo para renderizar directamente en el lienzo infinito interactivo.
- En cuanto abras tu archivo de diseño en Pencil, las herramientas de ejecución de trazo en canvas estarán sincronizadas con el proyecto.
