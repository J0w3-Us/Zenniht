# Reportes de Calidad, Interacción y Consistencia ZENIT (Estándar Impeccable)

Este documento estructura los hallazgos operativos y de diseño de interacción (UX/UI) detectados en el copiloto y panel de ZENIT, refinados bajo los principios de **Impeccable Design** (C:\Users\fitch\.agents\skills\impeccable) (claridad visual, jerarquía predecible, ausencia de estados contradictorios y respeto al flujo de atención del usuario clínico).

---

## Reporte 1: Falso rechazo y respuestas evasivas en consultas directas de inventario y clasificación de prioridades (Kraljic)

Problema detectado
Cuando el usuario solicita métricas concretas del inventario disponible y su distribución por categorías de prioridad (por ejemplo: "Dame un resumen actual del inventario, cuántas unidades hay disponibles y cómo se distribuyen los cuadrantes Kraljic" o "quiero saber las unidades disponibles y cómo se distribuyen en las prioridades"), el asistente de IA local evade la consulta o la rechaza por completo. En la primera interacción responde con una lista genérica de sus capacidades sin entregar datos, y en la segunda activa el mensaje de bloqueo de alcance ("Solo puedo ayudarte con inventario, ventas, riesgo de desabasto..."), contradiciendo sus propias funciones permitidas.   
image_87d8bd.png

Causa raíz

Falla en el mapeo de intenciones y tolerancia tipográfica: El clasificador de intención o el system prompt no logra vincular términos específicos del dominio de inventario (como "cuadrantes Kraljic" o "prioridades") ni tolera errores menores de escritura del usuario (como "unidadesdisponoibles" o "distribulyen") hacia la herramienta de consulta de inventario.   
image_87d8bd.png

Activación prematura de respuestas canónicas de rechazo: Ante términos que el modelo no reconoce en su plantilla estricta, opta por devolver la respuesta de delimitación de alcance en lugar de ejecutar la lectura del inventario general y agrupar los registros por categoría (Estratégico, Cuello de botella, Apalancado, Rutinario).

Impacto operativo
Bloquea la visibilidad del estado global del almacén y de la clasificación estratégica de los insumos, obligando al personal médico o de farmacia a reformular repetidamente preguntas básicas de inventario sin obtener los datos solicitados.

Propuesta de solución

Mapear categorías de prioridad al módulo de inventario: Vincular explícitamente conceptos como cuadrantes Kraljic, prioridades, clasificación y unidades disponibles con la consulta directa a la tabla de inventario, asegurando que el modelo sume las existencias y las desglose por categoría.

Mejorar la tolerancia semántica y ortográfica del prompt: Instruir al modelo para que interprete la intención real del usuario incluso cuando existan errores tipográficos o variaciones de redacción, priorizando la consulta a la base de datos de inventario antes de emitir mensajes de bloqueo.

## reporte 2: Contradicción entre el mensaje de error en texto y la entrega exitosa del widget de sugerencias de reabastoProblema detectado
Ante la consulta directa "Muéstrame las sugerencias de reabasto pendientes de aprobación", el asistente devuelve un mensaje textual de error afirmando que no pudo completar la solicitud ("No pude completar esa consulta con los datos de la farmacia. Revisa la información disponible e inténtalo de nuevo"), pero simultáneamente renderiza debajo la tarjeta interactiva "Sugerencias de reabasto" con el registro correspondiente (Insulina glargina).   Causa raíz
Existe una desconexión entre la capa de generación de texto del modelo local y el servicio que consulta la base de datos para poblar los componentes gráficos:Ejecución paralela desincronizada: El frontend o el orquestador consulta correctamente la tabla de sugerencias pendientes y renderiza el widget con los resultados reales, pero el modelo de lenguaje no recibe dicha respuesta en su contexto (o falla al interpretar el JSON devuelto), disparando por defecto su plantilla de error.Impacto operativo
Genera desconfianza e incertidumbre en el usuario final, ya que el texto afirma que la operación falló mientras la interfaz muestra registros activos listos para ser aprobados, haciendo dudar sobre si los datos desplegados están actualizados o corresponden a una consulta anterior.   Propuesta de soluciónInyectar el resultado del widget en el contexto del LLM: Asegurar que, cuando la consulta a la base de datos de sugerencias devuelva registros válidos, el modelo reciba el conteo y resumen de dichos registros para responder afirmativamente en texto antes de mostrar la tarjeta.Unificar el manejo de errores entre backend y UI: Si realmente ocurre un fallo en la consulta de datos, impedir que se renderice cualquier componente visual debajo del mensaje de error para mantener coherencia en toda la respuesta.

## reporte 3: Omisión de renderizado en tablas predefinidas ante consultas de series históricas con múltiples registros

Problema detectado
Cuando el usuario solicita el historial detallado de un producto en un rango amplio de fechas (por ejemplo: "Consulta el detalle y el historial de ventas de los últimos 14 días de Insulina glargina"), el asistente local devuelve los 14 registros diarios como una lista en texto plano (2026-10-30: 12 vendidas; 60 en existencia...), ignorando los componentes de tabla predefinidos del sistema para organizar grandes volúmenes de datos.   
image_87e36a.png

Causa raíz

Falta de mapeo del componente tabular al módulo de historial de ventas: Las reglas de presentación o plantillas de salida no están vinculando las series temporales de ventas/existencias con el componente de tabla predefinido de la interfaz, haciendo que el modelo vuelque el arreglo de datos directamente como texto corrido.

Ausencia de activación por umbral de volumen: El sistema no evalúa el conteo de filas devueltas (14 registros) para forzar automáticamente la estructuración tabular cuando se supera el límite establecido para texto plano.   
image_87e36a.png

Impacto operativo
Dificulta la lectura, comparación diaria de ventas y trazabilidad de variaciones de inventario (como reposiciones o caídas bruscas de stock) al obligar al usuario a leer línea por línea una lista extensa sin columnas alineadas.   
image_87e36a.png

Propuesta de solución

Vincular las consultas de historial al componente de tabla predefinido: Configurar el pipeline de respuesta para que toda consulta de movimientos o ventas históricas que devuelva múltiples fechas renderice automáticamente los datos en la tabla predefinida (con columnas estructuradas para Fecha, Unidades vendidas y Existencia).

Aplicar regla estricta de umbral de filas: Establecer en el formateador de salida que cualquier respuesta con más de un número mínimo de registros (por ejemplo, ≥ 5 elementos) se estructure obligatoriamente en formato de tabla en lugar de listado en texto plano.

## reporte 4: Persistencia de contradicción entre el mensaje textual de error y el despliegue del componente de sugerencias de reabasto

Problema detectado
Se confirma de manera recurrente que, al solicitar "Muéstrame las sugerencias de reabasto pendientes de aprobación", el asistente devuelve un mensaje de rechazo afirmando que no pudo completar la consulta ("No pude completar esa consulta con los datos de la farmacia. Revisa la información disponible e inténtalo de nuevo"), pero inmediatamente debajo renderiza la tabla/tarjeta "Sugerencias de reabasto" con los datos reales (Insulina glargina).   
image_87e6a9.png

Causa raíz
El flujo de ejecución presenta una falla de sincronización entre el backend de datos y la respuesta generada por el modelo local:

Mientras la interfaz recupera y despliega correctamente los registros de reabasto pendientes desde la base de datos, el modelo conversacional no recibe la confirmación de los resultados encontrados (o falla al validar el payload de respuesta), activando por defecto su mensaje genérico de error.

Impacto operativo
Crea confusión directa en el flujo de aprobación médica y de farmacia, ya que el texto niega la existencia o disponibilidad de datos mientras la interfaz presenta una acción activa (Aprobar), poniendo en duda la validez y vigencia de la sugerencia mostrada.   
image_87e6a9.png

Propuesta de solución

Vincular el contexto de salida del widget con el prompt del modelo: Garantizar que, cuando la consulta de sugerencias devuelva al menos un registro válido, el modelo reciba dichos datos antes de redactar su respuesta para confirmar la entrega en lugar de emitir el mensaje de fallo.

Bloquear componentes gráficos en estados de error: Asegurar que, si el sistema entra realmente en una excepción o fallo de consulta, la interfaz suprima el renderizado de la tarjeta de "Sugerencias de reabasto" para mantener coherencia entre texto y UI.

## Fallos en los logs

A partir de la traza de ejecución del servidor backend (Uvicorn) y del motor de inferencia (PyTorch Lightning), se identifican los siguientes hallazgos técnicos relevantes para el reporte de fallos:

1. Advertencia Crítica en el Modelo Predictivo (RuntimeWarning - Checkpoint obsoleto)
Evidencia en log: OpenJarvis\modelo\predecir.py:219: RuntimeWarning: Checkpoint antiguo: riesgo semanal aproximado bajo independencia diaria. Reentrena para evento semanal directo.

Descripción de la falla: El sistema está cargando un archivo de pesos (checkpoint) desactualizado del modelo TFT. Debido a esta versión antigua, el motor no calcula directamente la probabilidad de desabasto como un evento semanal continuo, sino que realiza una aproximación matemática asumiendo independencia diaria entre días consecutivos.

Impacto: Explica las imprecisiones, fechas desfasadas y el cálculo conservador o extremo en los porcentajes de riesgo de desabasto (como alertas fijas al 99.3% o 100%). Requiere reentrenar el modelo con la estructura actual de eventos semanales directos.

2. Cuello de Botella en Carga de Datos e Inferencia en CPU
Evidencia en log:

GPU available: False, used: False

predict_dataloader does not have many workers which may be a bottleneck. Consider increasing the value of the num_workers argument to num_workers=11

Descripción de la falla: Toda la inferencia del modelo predictivo se está ejecutando exclusivamente en CPU con un cargador de datos (DataLoader) de un solo hilo (num_workers=0 por defecto).

Impacto: Incrementa la latencia de respuesta en las peticiones POST /api/zenit/agente/chat cuando se invoca la predicción, generando tiempos de espera prolongados que pueden provocar timeouts o desincronización entre el modelo conversacional y el renderizado de tarjetas en el frontend.

3. Fallos Silenciosos en las Peticiones del Agente (HTTP 200 OK encubriendo errores lógicos)
Evidencia en log:

INFO: 127.0.0.1:50195 - "POST /api/zenit/agente/chat HTTP/1.1" 200 OK

INFO: 127.0.0.1:64494 - "POST /api/zenit/agente/chat HTTP/1.1" 200 OK (ejecutado dos veces consecutivas)

Descripción de la falla: Aunque el endpoint /api/zenit/agente/chat responde invariablemente con código de estado HTTP 200 OK sin arrojar excepciones de servidor (500), internamente el agente está devolviendo respuestas de bloqueo o error funcional en el cuerpo del mensaje. Asimismo, se observan peticiones duplicadas desde el mismo puerto cliente (64494), lo que evidencia reintentos automáticos o doble disparo de eventos desde la interfaz.

Impacto: Dificulta la detección de errores a nivel de monitoreo HTTP y provoca saturación innecesaria en el backend cuando se disparan consultas duplicadas.

4. Advertencias de Serialización y Deprecación en PyTorch Lightning
Evidencia en log:

Attribute 'loss' is an instance of nn.Module and is already saved during checkpointing.

Attribute 'logging_metrics' is an instance of nn.Module and is already saved during checkpointing.

isinstance(treespec, LeafSpec) is deprecated

Descripción de la falla: Durante la inicialización del modelo, PyTorch Lightning emite advertencias por guardar módulos redundantes (loss y logging_metrics) dentro de los hiperparámetros del checkpoint y por el uso de métodos internos deprecados en Python 3.13.

Impacto: Aunque no detienen la ejecución actual, incrementan el peso de los archivos de checkpoint, ensucian la salida de consola dificultando la lectura de errores reales y representan un riesgo de incompatibilidad en futuras actualizaciones de librerías.

## Scrips de fallos en los logs

INFO:     Will watch for changes in these directories: ['C:\\dev\\projects\\Zenith-Openjarvis\\OpenJarvis']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [2700] using WatchFiles
INFO:     Started server process [5984]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:57664 - "GET /api/zenit/estado HTTP/1.1" 200 OK
INFO:     127.0.0.1:64442 - "GET /api/zenit/estado HTTP/1.1" 200 OK
INFO:     127.0.0.1:52334 - "GET /api/zenit/agente/estado HTTP/1.1" 200 OK
INFO:     127.0.0.1:50195 - "GET /api/zenit/agente/estado HTTP/1.1" 200 OK
C:\Users\fitch\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\lightning\pytorch\utilities\parsing.py:213: Attribute 'loss' is an instance of `nn.Module` and is already saved during checkpointing. It is recommended to ignore them using `self.save_hyperparameters(ignore=['loss'])`.
C:\Users\fitch\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\lightning\pytorch\utilities\parsing.py:213: Attribute 'logging_metrics' is an instance of `nn.Module` and is already saved during checkpointing. It is recommended to ignore them using `self.save_hyperparameters(ignore=['logging_metrics'])`.
GPU available: False, used: False
TPU available: False, using: 0 TPU cores
💡 Tip: For seamless cloud logging and experiment tracking, try installing [litlogger](https://pypi.org/project/litlogger/) to enable LitLogger, which logs metrics and artifacts automatically to the Lightning Experiments platform.      
💡 Tip: For seamless cloud uploads and versioning, try installing [litmodels](https://pypi.org/project/litmodels/) to enable LitModelCheckpoint, which syncs automatically with the Lightning model registry.
C:\Users\fitch\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\lightning\pytorch\utilities\_pytree.py:21: `isinstance(treespec, LeafSpec)` is deprecated, use `isinstance(treespec, TreeSpec) and treespec.is_leaf()` instead.
C:\Users\fitch\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\lightning\pytorch\trainer\connectors\data_connector.py:434: The 'predict_dataloader' does not have many workers which may be a bottleneck. Consider increasing the value of the `num_workers` argument` to `num_workers=11` in the `DataLoader` to improve performance.
C:\dev\projects\Zenith-Openjarvis\OpenJarvis\modelo\predecir.py:219: RuntimeWarning: Checkpoint antiguo: riesgo semanal aproximado bajo independencia diaria. Reentrena para evento semanal directo.
  warnings.warn("Checkpoint antiguo: riesgo semanal aproximado bajo independencia diaria. Reentrena para evento semanal directo.", RuntimeWarning)
INFO:     127.0.0.1:50195 - "POST /api/zenit/agente/chat HTTP/1.1" 200 OK
INFO:     127.0.0.1:64494 - "POST /api/zenit/agente/chat HTTP/1.1" 200 OK
INFO:     127.0.0.1:64494 - "POST /api/zenit/agente/chat HTTP/1.1" 200 OK
INFO:     127.0.0.1:64301 - "OPTIONS /api/zenit/agente/chat HTTP/1.1" 200 OK
INFO:     127.0.0.1:64301 - "POST /api/zenit/agente/chat HTTP/1.1" 200 OK
