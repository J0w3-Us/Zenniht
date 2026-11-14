# Plan de armado

## Paso 0. Inventario de Jarbis (antes de tocar código)
Escribe `docs/JARBIS_INVENTARIO.md` con: lenguaje y framework, estructura de carpetas, dependencias, llamadas a APIs externas o de pago, uso de claves, base de datos que usa, cómo se arranca, y la **licencia**. Marca qué se conserva, qué se reemplaza y qué se borra. No modifiques nada hasta que el equipo revise ese archivo.

## Paso 1. Limpieza
Quita APIs de pago, nube y claves. Verifica que el repo arranca sin internet.

## Paso 2. Datos (Hito de Entrada)
`python data/generar_datos.py` genera `ventas.csv` y `zenith.db`. Implementa `db.py` y la carga del CSV a SQLite desde el backend.

## Paso 3. Modelo (Hito de Procesamiento)
- `modelo/entrenar_tft.py`: TFT con `pytorch-forecasting`, `hidden_size` 16, CPU, horizonte de 7 días. Entrena con los primeros 63 días y guarda el checkpoint en `modelo/zenith_tft.ckpt`.
- `modelo/predecir.py`: carga el checkpoint, predice los 50 productos y mide el tiempo en milisegundos.
- Calcula el F1-Score sobre los últimos 27 días.

## Paso 4. Backend
Endpoints sobre el backend de Jarbis: `/cargar` (CSV a SQLite), `/predecir` (probabilidad de desabasto por producto), `/ordenes` (orden sugerida y aprobación).

## Paso 5. Kraljic
`kraljic.py` pondera la alerta según el cuadrante y ordena la lista: Estratégico y Cuello de botella primero.

## Paso 6. Interfaz (Hito de Salida)
Tabla de 50 filas, celdas rojas en desabasto, botón de aprobar orden. Si Jarbis tiene chat, déjalo como consultas con plantillas validadas, sin LLM de pago.

## Paso 7. Ensayo final
En una laptop sin internet: instalar desde `requirements.txt`, cargar el CSV, predecir, ver las celdas rojas. Cronometra la inferencia.

## Riesgos
- PyTorch es la instalación que más falla: prueba la instalación en cada laptop del equipo y fija versiones con `pip freeze` cuando funcione.
- Entrena antes de la clase y guarda el checkpoint en el repo; en la presentación solo se hace inferencia.
- Con pocos positivos, compara el TFT contra una regla de umbral solo como referencia; no la uses como reemplazo.
