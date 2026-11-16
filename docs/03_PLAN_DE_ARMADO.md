# Plan de armado

## Decisión de inteligencia (fija para la actividad)
ZENIT usará **un solo modelo de predicción: Temporal Fusion Transformer (TFT)** con `pytorch-forecasting`, `hidden_size=16`, ejecución local en CPU y horizonte de 7 días. Es el algoritmo requerido por el escenario real y por las Secciones 1, 2 y 3.

No se integrarán Gemini, NIM ni otros LLM o APIs, aunque tengan nivel gratuito: dependen de Internet y de servicios externos, y no forman parte del modelo evaluado. No se cambiarán el algoritmo, el dataset, el umbral de alerta ni las métricas congeladas en las Secciones 2 y 3. Si se conserva chat de OpenJarvis, solo podrá usar consultas/plantillas validadas; no calculará ni modificará predicciones.

### Referencia externa documentada (fuera de ZENIT)
Como referencia para una prueba independiente de chat, la documentación oficial consultada el 15 de noviembre de 2026 muestra **Gemini 3.8 Flash** con acceso en el nivel gratuito ([modelos](https://ai.google.dev/gemini-api/docs/models), [precios](https://ai.google.dev/gemini-api/docs/pricing)). Esto no cambia la arquitectura de ZENIT ni agrega dependencias/configuración al repositorio: la prueba requiere Internet y una clave propia, queda fuera del código, los datos, la demostración y las métricas. No se enviarán datos reales de farmacia; las condiciones, cuotas y disponibilidad del proveedor pueden cambiar.

## Paso 0. Inventario de Jarbis (antes de tocar código)
Escribe `docs/JARBIS_INVENTARIO.md` con: lenguaje y framework, estructura de carpetas, dependencias, llamadas a APIs externas o de pago, uso de claves, base de datos que usa, cómo se arranca, y la **licencia**. Marca qué se conserva, qué se reemplaza y qué se borra. No modifiques nada hasta que el equipo revise ese archivo.

## Paso 1. Limpieza
Aparta del flujo del prototipo las APIs de pago o gratuitas, proveedores en nube, llamadas externas y claves. Conserva la licencia de OpenJarvis y sus avisos aplicables. Verifica que el arranque de la aplicación y sus funciones del prototipo no requieren Internet ni servidores externos.

## Paso 2. Datos (Hito de Entrada)
`python data/generar_datos.py` genera `ventas.csv` y `zenith.db`. Implementa `db.py` y la carga del CSV a SQLite desde el backend. Comprueba las 8 columnas acordadas, 4,500 filas, 50 productos, 90 días, cero nulos y la distribución Kraljic 10/15/10/15. La carga debe informar el resultado localmente.

## Paso 3. Modelo (Hito de Procesamiento)
- `modelo/entrenar_tft.py`: entrena el único modelo de predicción, TFT con `pytorch-forecasting`, `hidden_size=16`, CPU y horizonte de 7 días, con los primeros 63 días; guarda el checkpoint en `modelo/zenith_tft.ckpt`.
- El objetivo del TFT es el quiebre diario (`existencia = 0`) en cada uno de los 7 pasos. Calcula el peso de la clase positiva con la proporción negativos/positivos del bloque de entrenamiento, corrige el sesgo resultante de la pérdida ponderada y agrega el riesgo semanal como `1 - producto(1 - p_diaria)`, bajo la suposición explícita de independencia entre días. Reporta el conteo de positivos y el peso.
- `modelo/predecir.py`: carga el checkpoint ya entrenado, produce una predicción para cada uno de los 50 productos y mide la inferencia por lote en milisegundos con `time.perf_counter()`. Separa el tiempo de carga/arranque del modelo del tiempo medido de inferencia.
- El criterio binario del Hito de Procesamiento es **menos de 1,000 ms** por lote con el modelo cargado. Antes de la demostración, repite la medición 30 veces en la laptop más lenta del equipo y reporta el percentil 95; no subas el umbral de 1,000 ms.
- Calcula el F1-Score de la alerta a 7 días con ventanas rodantes completas contenidas en los últimos 27 días: fechas de corte 2026-10-16 a 2026-11-05, 21 cortes × 50 productos. Reporta positivos y no incorpora otros productos, fechas ni modelos.
- `requirements.txt` fija las versiones del entorno ZENIT y selecciona el wheel CPU de PyTorch. Prepara las dependencias antes de la demostración; el entrenamiento e inferencia no descargan paquetes ni requieren Internet.

## Paso 4. Backend
`zenit_api.py` expone una API FastAPI local, independiente del motor conversacional de OpenJarvis: `/api/zenit/cargar` (acepta solo el CSV canónico y lo guarda en SQLite), `/api/zenit/predecir` (devuelve la probabilidad TFT por producto) y `/api/zenit/ordenes` (consulta y aprueba órdenes sugeridas). Se liga a `127.0.0.1`; no requiere CORS, nube ni APIs externas. La vista usa la interfaz React de OpenJarvis, pero no inicia su chat, telemetría ni analítica en la ruta ZENIT. No inventes cantidades de compra mientras no exista una regla de reabasto acordada. La compra nunca se ejecuta automáticamente.

## Paso 5. Kraljic
`kraljic.py` organiza la prioridad de las alertas por cuadrante, mostrando Estratégico y Cuello de botella primero. No reemplaza ni altera la probabilidad producida por el TFT ni el umbral visual de 0.50.

## Paso 6. Interfaz (Hito de Salida)
La ruta `/zenit` de la interfaz React muestra exactamente 50 filas después de cargar el dataset. Pinta de rojo los productos cuya probabilidad de desabasto sea **≥ 0.50** y presenta la orden sugerida como pendiente de aprobación; la cantidad queda «Por definir» hasta acordar una regla de reabasto. La fecha de corte de la demostración es 2026-10-22; valida las alertas contra la existencia real de los 7 días siguientes, según la Sección 3. El dueño aprueba la orden explícitamente. Una inferencia sin alertas se muestra como tal, sin órdenes prefabricadas. Si se conserva el chat de Jarbis, úsalo solo para consultas con plantillas validadas, sin LLM.

## Paso 7. Ensayo final
En una laptop sin Internet: instalar las dependencias de `requirements.txt`, iniciar la API local desde la raíz con `python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000` e iniciar la interfaz desde `OpenJarvis\frontend` con `npm run dev -- --host 127.0.0.1`. Abrir `http://127.0.0.1:5173/zenit`, cargar el CSV, ejecutar el TFT local, comprobar el tiempo de inferencia y revisar las celdas rojas y la aprobación manual. Verifica los tres hitos binarios de la Sección 3. No uses servicios externos durante el ensayo.

## Riesgos
- PyTorch es la instalación que más falla: prueba el entorno fijado en cada laptop del equipo y verifica que `torch.cuda.is_available()` sea falso para confirmar la ruta CPU.
- Entrena antes de la clase y guarda el checkpoint en el repo; en la presentación solo se hace inferencia.
- Con pocos positivos, compara el TFT contra una regla de umbral solo como referencia; no la uses como reemplazo.
- El umbral de 1,000 ms aún debe validarse en la laptop más lenta; no lo presentes como medido hasta ejecutar las repeticiones indicadas.
- La lista de modelos de `jarvis model list` puede incluir motores remotos (por ejemplo, NIM); que un modelo aparezca allí no lo convierte en parte de ZENIT ni en una alternativa al TFT.
