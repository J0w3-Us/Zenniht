# ZENIT: alcance logrado

**Fecha:** 18 de noviembre de 2026  
**Audiencia:** equipo de desarrollo (IA)  
**Tipo:** guía práctica de alcance

## 1. Propósito

Esta guía establece qué hace el prototipo ZENIT, qué debe hacer según las restricciones acordadas, qué no forma parte del producto y qué queda pendiente. Úsala antes de proponer o implementar cambios para mantener el trabajo dentro del alcance.

ZENIT es una herramienta local de apoyo para anticipar el desabasto de medicamentos e insumos en una farmacia ficticia, **La Esperanza**. No ofrece conversación generativa ni es un sistema integral para administrar una farmacia; incluye un copiloto local de consultas limitadas y respuestas predefinidas.

## 2. Alcance logrado en el prototipo

| Área | Capacidad implementada |
|---|---|
| Datos | Valida y carga el CSV canónico con 4,500 registros, 50 productos y 90 días a SQLite local. La API expone la existencia por producto del último día registrado y la fecha de ese corte. |
| Predicción | Ejecuta el Temporal Fusion Transformer de `pytorch-forecasting`, con `hidden_size=16`, en CPU y con horizonte de 7 días. |
| Eficiencia de CPU | Limita PyTorch a un hilo intraoperatorio y uno interoperativo durante entrenamiento e inferencia; el uso debe verificarse en el equipo más modesto. |
| Riesgo | Corrige la salida por la ponderación de clases y calcula el riesgo semanal como `1 - producto(1 - p_diaria)`, bajo la suposición de independencia entre días. |
| Alertas | Marca como alerta el riesgo TFT de 0.50 o superior. La priorización Kraljic organiza los resultados, pero no cambia probabilidades ni el umbral. |
| Consulta local | El copiloto consulta existencias, productos, alertas TFT y sugerencias con respuestas predefinidas; permite abrir el inventario o una sugerencia. No usa LLM ni envía información fuera de la aplicación. |
| Sugerencias | Crea sugerencias pendientes para revisión. La persona debe aprobarlas explícitamente; la cantidad queda sin definir. |
| Interfaz | Organiza Resumen, Inventario y Sugerencias con navegación adaptable y áreas desplazables. El resumen muestra unidades disponibles, productos sin existencias, alertas TFT y sugerencias pendientes, diferenciando el último corte de stock de la fecha de predicción. Los KPI abren la lista o el filtro correspondiente. Inventario, alertas y sugerencias muestran hasta 20 elementos por página; el historial del copiloto no se pagina. El copiloto local se abre desde una burbuja inferior. |

El flujo de interfaz está en [ZenitPage.tsx](../OpenJarvis/frontend/src/pages/ZenitPage.tsx) y [InventoryTable.tsx](../OpenJarvis/frontend/src/components/Zenit/InventoryTable.tsx). Las rutas de backend están en [zenit_api.py](../OpenJarvis/zenit_api.py), la persistencia en [db.py](../OpenJarvis/db.py), y la inferencia en [predecir.py](../OpenJarvis/modelo/predecir.py).

## 3. Flujo práctico actual

1. Preparar e iniciar la API local y la interfaz desde el entorno del proyecto.
2. Cargar el CSV canónico de ZENIT. El backend verifica que sea el archivo esperado y valida su estructura antes de guardarlo en SQLite.
3. Elegir una fecha de corte válida y solicitar una predicción.
4. El backend ejecuta el TFT local para los 50 productos y devuelve las probabilidades, las alertas y el tiempo de inferencia.
5. Revisar el resumen y la tabla de 50 productos; utilizar filtros, búsqueda o el copiloto local para consultar datos del inventario.
6. Si corresponde, aprobar una sugerencia individualmente. La aprobación cambia el estado local de la sugerencia; no realiza una compra.

Si falta el checkpoint, el CSV es inválido o la inferencia falla, debe mostrarse un error explícito. No se deben sustituir los resultados por datos de ejemplo, reglas u otro modelo.

## 4. Límites del modelo y de los datos

- El universo de demostración es fijo: una farmacia ficticia, 50 productos, 90 días y 4,500 filas.
- Se utiliza el dataset canónico; no se deben ampliar productos, sucursales o fechas para mejorar una métrica.
- El modelo es únicamente el TFT local en CPU. No se reemplaza por un LLM, una API, una regla de negocio ni otro modelo.
- Los primeros 63 días se destinan al entrenamiento y la evaluación usa ventanas rodantes dentro de los últimos 27 días, según la metodología acordada.
- El CSV incluye caducidad y temperatura, pero su presencia no implica que existan alertas de caducidad o monitoreo de cadena de frío. La fecha de caducidad no forma parte de las variables usadas por el TFT actual.
- El dato `requiere_refrigeracion` es una característica del producto, no una lectura de un sensor.
- Kraljic sirve para priorizar la revisión. No debe alterar el resultado estadístico del TFT.
- Una sugerencia no define una cantidad de compra hasta que el equipo acuerde una regla de reabasto.

Las restricciones completas están en [CLAUDE.md](../CLAUDE.md), [02_RESTRICCIONES_SECCION_1.md](./02_RESTRICCIONES_SECCION_1.md) y [03_PLAN_DE_ARMADO.md](./03_PLAN_DE_ARMADO.md).

## 5. Funciones fuera de alcance

No forman parte de este prototipo:

- Recetas, pacientes, citas médicas, diagnóstico o expedientes.
- Varias farmacias, sucursales o un catálogo mayor de productos.
- Sensores IoT o monitoreo de temperatura en tiempo real.
- Búsqueda en Internet, comparación de proveedores o contacto con proveedores.
- Compras, pagos o generación automática de órdenes ejecutables.
- Cantidades de reabasto calculadas sin una regla aprobada.
- Chat generativo, respuestas de LLM o APIs en la nube.
- Analítica remota, telemetría o servicios externos requeridos para ejecutar el flujo ZENIT.

Estas exclusiones son parte del alcance de la actividad, no funciones pendientes que deban agregarse automáticamente.

## 6. Validación y trabajo pendiente

La implementación de una función y la validación de su hito son cosas distintas. El estado registrado en [05_SECCION_3_HITOS_VALIDACION.md](./05_SECCION_3_HITOS_VALIDACION.md) debe actualizarse cuando se haga una medición nueva.

### Pruebas con datos locales

Las pruebas de KPI de existencias leen el CSV canónico y validan el corte real de los 50 productos. La prueba de integración de la API carga ese CSV en SQLite temporal y ejecuta el checkpoint TFT local para comprobar las probabilidades, alertas y sugerencias que alimentan los KPI; no sustituye la inferencia por resultados preparados.

### Procesamiento y consumo de CPU

La medición más reciente del 18 de noviembre de 2026 en la Intel Core i5-1235U limitó PyTorch a un hilo intraoperatorio y uno interoperativo. Tras una pasada de calentamiento, 30 lotes de 50 productos dieron p95 TFT de **240.44 ms**, mediana de **214.19 ms** y p95 de llamada completa de **509.20 ms**. La inicialización y carga del checkpoint tomó **2,344.33 ms**, medida aparte; el proceso promedió **0.95 núcleos equivalentes** durante las inferencias. El hito de 1,000 ms se cumple en este equipo.

La corrida anterior del 17 de noviembre registró 69.60 ms de p95 TFT. Como la nueva medición es más lenta y las condiciones no se controlaron para compararlas, no se sustituye el resultado reciente por el anterior ni se atribuye una causa. El límite de un hilo reduce la contención de PyTorch, pero no garantiza una temperatura concreta ni limita otros procesos. El objetivo de CPU de 3 núcleos aún no se ha verificado en un equipo de esas características.

### Calidad de las alertas

La Sección 3 registra **F1 = 0.0000** y 70 positivos reales en 1,050 casos. Para la fecha de demostración 2026-10-22, ese registro indica que el modelo no emitió alertas pese a que seis productos llegan a existencia cero en los siete días siguientes. Por tanto, el hito de salida **no está cumplido**, aunque la inferencia sea rápida y el modelo esté conectado a la interfaz.

No se deben bajar el umbral ni fabricar alertas para aparentar éxito. El siguiente trabajo de modelo debe investigar y mejorar el TFT manteniendo el algoritmo, el dataset, el horizonte y el umbral acordados; luego debe repetirse la evaluación.

### Comprobaciones pendientes

- Ejecutar `python -m modelo.medir_rendimiento` en la laptop más lenta (idealmente la de 3 núcleos) y conservar la evidencia.
- Ensayar el flujo completo sin Internet, incluida la carga, predicción y revisión del resultado.
- Confirmar la carga del archivo desde la interfaz en el entorno de demostración.
- Revalidar la predicción contra las existencias reales de los siete días futuros y reportar el F1 y los conteos.
- No afirmar que el hito de salida está cumplido hasta que las alertas reales satisfagan el criterio acordado.

## 7. Guía para cambios futuros

Antes de modificar el proyecto:

1. Identifica qué hito o requisito atiende el cambio.
2. Mantén el universo de datos, el TFT, el horizonte y el umbral congelados, salvo que el equipo revise formalmente las restricciones de la actividad.
3. Conserva los errores explícitos: no agregues resultados de respaldo ni degradaciones silenciosas.
4. Mantén la aprobación humana y no inventes cantidades de compra.
5. Añade pruebas enfocadas al comportamiento nuevo y vuelve a medir el hito afectado.
6. Separa en la documentación las capacidades implementadas, las verificadas y las propuestas.

## 8. Propuestas para evaluar, no compromisos del alcance actual

Las siguientes son posibles tareas de desarrollo dentro del objetivo de predicción, sujetas a revisión del equipo:

- Analizar el F1 bajo y la diferencia entre las alertas TFT y los quiebres observados; verificar datos, ventanas, ponderación y evaluación sin cambiar el umbral para mejorar artificialmente la métrica.
- Añadir una forma reproducible de ejecutar las 30 mediciones y reportar p95, mediana, versión del equipo y tiempo de carga separado del tiempo de inferencia.
- Mejorar la presentación del estado de validación para distinguir claramente “predicción calculada” de “predicción que cumple el hito”.
- Completar y documentar el ensayo integral sin conexión en el equipo de demostración.

No se propone ampliar el producto con recetas, proveedores, sucursales, sensores o conversación generativa. Cualquier propuesta que contradiga [CLAUDE.md](../CLAUDE.md) debe rechazarse o reformularse antes de escribir código.
