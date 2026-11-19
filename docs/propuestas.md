# Prpuestas que puede hacer el chat de Zenith

**creacion**
1. crear registro de excel sobre las ventas de la farmacia ficticia, con las columnas: fecha, producto, cantidad vendida, precio unitario, total de venta, existencia inicial, existencia final y requiere_refrigeracion. El archivo debe tener 4,500 filas (50 productos × 90 días) y debe ser generado por el script `data/generar_datos.py` con semilla fija para garantizar reproducibilidad.

2. creacion de recomendaciones de compra: el chat puede generar sugerencias de compra basadas en las predicciones del modelo TFT y las alertas generadas por la probabilidad de desabasto. Estas sugerencias se presentan como pendientes de aprobación y no ejecutan compras automáticamente.

3. Puede generar cotizaciones de compra ficticias para los productos con alerta de desabasto, basadas en los datos de ventas y predicciones del modelo. Estas cotizaciones son solo para fines de demostración y no representan transacciones reales.

**uso**
1. Uso de la herramienta de predicción: el chat puede ejecutar el modelo de predicción Temporal Fusion Transformer (TFT) entrenado para generar probabilidades de desabasto a 7 días para cada uno de los 50 productos en el inventario. El chat puede solicitar la predicción para una fecha de corte específica y recibir las probabilidades calculadas por el modelo.

2. Uso de la base de datos SQLite: el chat puede realizar consultas a la base de datos SQLite (`zenith.db`) para obtener información sobre las ventas, inventario y predicciones almacenadas. Puede consultar los registros existentes, filtrar por producto o fecha, y obtener información relevante para la toma de decisiones.

3, Uso de la interfaz de excel ya que puede generar un archivo, pero no puede modificarlo ni agregar nuevas columnas o filas. El chat puede leer los datos del archivo generado y utilizarlos para realizar análisis o generar reportes, pero no puede alterar la estructura del archivo original.

4. Uso de la interfaz de cotización: el chat puede generar cotizaciones de compra ficticias para los productos con alerta de desabasto, basadas en los datos de ventas y predicciones del modelo. Estas cotizaciones son solo para fines de demostración y no representan transacciones reales.
**Limitaciones**
1.  Limitaciones hacia la base de datos: el chat no puede modificar la estructura de la base de datos SQLite ni agregar nuevas tablas o columnas. Solo puede interactuar con los datos existentes y realizar consultas o actualizaciones dentro de los límites definidos por el prototipo.

2. Limitaciones hacia el modelo de predicción: el chat no puede cambiar el algoritmo de predicción (Temporal Fusion Transformer), ni modificar sus parámetros, ni reemplazarlo por otro modelo. Solo puede utilizar el modelo entrenado para generar predicciones basadas en los datos existentes.

3. El modelo no puede revelar información sensible ni datos de pacientes, ya que el prototipo utiliza datos sintéticos y no tiene acceso a información real de farmacias o pacientes solo a los medicamentos dentro del inventario.

4. Prporciona solo datos que sean necesarios para la predicción de desabasto y no puede generar información adicional que no esté relacionada con el alcance del prototipo.