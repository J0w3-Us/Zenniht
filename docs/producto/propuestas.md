# Capacidades, Arquitectura de IA y Reglas de Seguridad de ZENIT

Este documento consolida la visión completa del sistema ZENIT, combinando las **capacidades operativas de inventario farmacéutico**, la **arquitectura técnica híbrida (IA analítica + LLM)** y las **barreras de seguridad (*guardrails*)** para garantizar la integridad de los datos y evitar cualquier riesgo operacional.

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

### A. Creación y Generación de Recursos
1. **Generación y Exportación de Datasets de Inventario:**
   - Creación de archivos tabulares (CSV/Excel) estructurados con los campos oficiales: `fecha`, `producto`, `cantidad_vendida`, `precio_unitario`, `total_venta`, `existencia_inicial`, `existencia_final` y `requiere_refrigeracion`.
   - Inicialización rápida con el dataset canónico reproducible (4,500 registros: 50 productos × 90 días con semilla fija vía `data/generar_datos.py`).
2. **Recomendaciones Inteligentes de Compra (Reabastecimiento):**
   - Propuestas automatizadas de reorden calculadas a partir del cruce de:
     - Probabilidad de desabasto a 7 días ($\ge 0.50$).
     - Clasificación del cuadrante Kraljic (dando máxima urgencia a productos *Estratégicos* y *Cuellos de Botella*).
     - Ritmo de consumo promedio reciente.
   - Presentación de las órdenes como **pendientes de aprobación** para el operador.
3. **Simulación y Cotizaciones Estimadas de Compra:**
   - Elaboración de borradores de cotizaciones y pedidos estimados ante riesgo inminente, desglosando volumen sugerido y costo aproximado según histórico de precios unitarios.

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
