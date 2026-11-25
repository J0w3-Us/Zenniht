# Capacidades, Arquitectura de IA y Reglas de Seguridad de ZENIT (Visión Futura)

> [!IMPORTANT]
> **Separación de alcance (leer antes de implementar):** Este documento describe **propuestas futuras de evolución** posteriores al prototipo de la Actividad 3.
>
> El **prototipo actual congelado** en [CLAUDE.md](../../CLAUDE.md), [02_RESTRICCIONES_SECCION_1.md](../especificaciones/02_RESTRICCIONES_SECCION_1.md) y [Alcance_logrado.md](../guias/Alcance_logrado.md) exige estrictamente:
> - **Sin LLM ni APIs en la nube** (el copiloto actual es 100% local con respuestas deterministas sobre SQLite/TFT).
> - **Sin cantidades automáticas de compra ni cotizaciones/precios** (las órdenes sugeridas mantienen `cantidad_sugerida = null` / «Por definir» hasta que el equipo apruebe una regla de reabasto).
> - **Dataset canónico cerrado de 8 columnas exactas:** `producto, fecha, unidades_vendidas, existencia, cuadrante_kraljic, requiere_refrigeracion, fecha_caducidad, temperatura`.
>
> Ninguna propuesta de este archivo reemplaza las restricciones de la Actividad 3 sin acuerdo explícito del equipo.

Este documento consolida la visión futura de evolución del sistema ZENIT, combinando las **capacidades operativas de inventario farmacéutico**, una posible **arquitectura técnica híbrida (IA analítica + LLM)** y las **barreras de seguridad (*guardrails*)** para garantizar la integridad de los datos y evitar cualquier riesgo operacional.

---

## 1. Contexto y Propósito del Sistema

ZENIT es una plataforma inteligente diseñada para resolver el problema crítico del desabasto y merma de medicamentos en farmacias independientes (caso base: farmacia comunitaria ficticia *"La Esperanza"*).

El sistema apoya la toma de decisiones mediante:
- Monitoreo continuo de existencias y ritmo de venta.
- Pronóstico probabilístico de desabasto a 7 días.
- Priorización estratégica basada en la **Matriz de Kraljic** (Estratégico, Cuello de botella, Apalancamiento, No crítico).
- Asistencia conversacional y operativa a través de un **Servicio de Inteligencia Artificial**.

---

## 2. Capacidades y Propuestas del Asistente de IA

El chat/copiloto de ZENIT actúa como un orquestador inteligente que puede ejecutar o coordinar las siguientes acciones:

### A. Creación y Generación de Recursos (Propuestas Futuras)
1. **Generación y Exportación de Datasets de Inventario:**
   - Inicialización rápida con el dataset canónico reproducible actual (4,500 registros: 50 productos × 90 días con semilla fija vía `data/generar_datos.py` y las 8 columnas oficiales: `producto`, `fecha`, `unidades_vendidas`, `existencia`, `cuadrante_kraljic`, `requiere_refrigeracion`, `fecha_caducidad` y `temperatura`).
   - *(Evolución futura, fuera del prototipo actual)*: exportación extendida a Excel/CSV con campos comerciales adicionales (por ejemplo, precios unitarios y totales de venta) cuando el alcance deje de estar congelado.
2. **Recomendaciones Inteligentes de Compra (Reabastecimiento):**
   - En el prototipo actual, el sistema genera sugerencias **pendientes de aprobación** cuando la probabilidad TFT a 7 días es $\ge 0.50$, priorizadas con Kraljic y con cantidad sin definir.
   - *(Evolución futura)*: cálculo de volumen sugerido cuando el equipo formalice y apruebe una regla de reabasto.
3. **Simulación y Cotizaciones Estimadas de Compra *(Evolución futura — fuera del prototipo actual)*:**
   - Elaboración de borradores de cotizaciones y pedidos estimados ante riesgo inminente, una vez que exista catálogo de precios y regla de cantidades aprobada.

### B. Herramientas y Servicios Disponibles para la IA
1. **Servicio Conversacional y Agéntico (LLM Híbrido/Multimodelo):**
   - Compatible tanto con modelos remotos (Gemini API, OpenAI GPT, Claude) como con modelos locales de código abierto (vía Ollama, vLLM o el motor integrado de OpenJarvis).
   - Capacidad de responder consultas en lenguaje natural, explicar la causa del riesgo de un producto, resumir el estado del inventario y asesorar sobre prioridades de abastecimiento.
2. **Motor de Predicción Especializado (TFT - Temporal Fusion Transformer):**
   - Modelo de aprendizaje profundo para series de tiempo (`pytorch-forecasting`, `hidden_size=16`, CPU local) que calcula el riesgo acumulado a 7 días:
     $$\text{Riesgo semanal} = 1 - \prod_{t=1}^{7} (1 - p_{\text{diaria}, t})$$
   - La IA puede invocar este motor para fechas de corte específicas (`fecha_corte`) e interpretar los resultados para el usuario.
3. **Persistencia e Historial (SQLite - `zenith.db`):**
   - Consultas dinámicas sobre ventas históricas, existencias por corte, inferencias previas y bitácora de órdenes.
4. **Flujo de Control y Aprobación de Órdenes:**
   - Gestión del ciclo de vida de las sugerencias (transición de `pendiente` a `aprobada`) y registro de decisiones del operador.

---

## 3. Barreras de Seguridad y Reglas de Protección (*Guardrails*)

Para asegurar que el modelo de IA opere de forma confiable sin comprometer la base de datos ni los procesos del negocio, se aplican las siguientes restricciones estrictas:

```
[ Usuario / Chat ]
        │
        ▼
[ Guardrails de la IA ] ──(Detección de comandos prohibidos / PHI)──► [ Bloqueo Inmediato ]
        │
   (Vía API Segura)
        ├────────► [ SQLite ]  (Solo consultas SELECT y vistas de lectura)
        ├────────► [ Backend ] (Endpoints validados: /cargar, /predecir, /ordenes/aprobar)
        └────────► [ Motor TFT / IA ] (Cálculo de riesgo probabilístico)
```

1. **Inmutabilidad de la Estructura de Datos (DDL Prohibido):**
   - La IA tiene **estrictamente prohibido** ejecutar sentencias destructivas (`DROP`, `ALTER`, `TRUNCATE`, `DELETE`) sobre las tablas de `zenith.db`.
   - Cualquier consulta generada por la IA debe limitarse a operaciones de lectura (`SELECT`) o pasar a través de contratos de API previamente definidos en el backend (`zenit_api.py`).

2. **Aprobación Humana Obligatoria (*Human-in-the-Loop*):**
   - La IA **nunca** ejecuta transacciones de compra reales, pagos financieros ni contacta a proveedores de forma autónoma.
   - Las órdenes generadas se mantienen en estado `pendiente`. La transición a `aprobada` requiere confirmación humana explícita en la interfaz.

3. **Confidencialidad Médica y Privacidad (Sin PHI):**
   - El sistema opera únicamente con métricas de inventario comercial y medicamentos.
   - Se prohíbe la ingestión, inferencia o almacenamiento de datos personales de pacientes, recetas médicas o diagnósticos clínicos.

4. **Integridad del Código y Entorno Local:**
   - La IA puede generar reportes y datasets dentro de las rutas designadas (`data/`), pero no tiene permisos para sobreescribir archivos del núcleo del backend, frontend o configuraciones críticas del sistema sin validación.
   - En caso de falla en el motor de predicción o desconexión, el sistema emite un error explícito en lugar de inventar datos o alucinar predicciones sintéticas no verificadas.
