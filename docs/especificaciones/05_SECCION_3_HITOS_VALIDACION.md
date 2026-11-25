# Sección 3: Hitos de validación mínima (criterios de éxito)

Cierra el prototipado de ZENIT. Continúa `CLAUDE.md`, la Sección 1 (`docs/02_RESTRICCIONES_SECCION_1.md`) y la Sección 2 (`docs/04_SECCION_2_ARQUITECTURA_FRUGAL.md`). Define cómo se demuestra al docente que la lógica funciona a escala. Cada hito es **binario** (funciona / no funciona), se verifica en vivo en una computadora personal, sin red externa ni servidores, con herramientas gratuitas. **No se introducen datos, métricas ni elementos nuevos:** todo lo de abajo sale de las Secciones 1 y 2.

## Elementos comprometidos (congelados)
| Elemento | Valor | Origen |
| --- | --- | --- |
| Dataset | `data/ventas.csv`: 4,500 filas, 50 productos × 90 días, 8 columnas (`producto, fecha, unidades_vendidas, existencia, cuadrante_kraljic, requiere_refrigeracion, fecha_caducidad, temperatura`) | Sección 1 |
| Huella SHA-256 del CSV | `1826980b24abea8784d6ba63c7f05f3b3aa9b434632bc976e7627ceb2ea43f7b` (verificar con `sha256sum data/ventas.csv`) | Sección 1 |
| Algoritmo | Temporal Fusion Transformer local, CPU, horizonte de 7 días; el quiebre diario se agrega como riesgo semanal | Secciones 1 y 2 |
| Regla de alerta | Probabilidad de desabasto ≥ 0.50 → celda roja y orden sugerida pendiente | Sección 2 |
| Entrenamiento / evaluación | Días 1 a 63 (2026-08-15 a 2026-10-16) / últimos 27 días (2026-10-17 a 2026-11-12) | Sección 1 |
| Costo | 0.00 MXN; herramientas de medición y visualización gratuitas | Sección 2 |

## 1. Tabla de hitos

| Hito | Descripción | Estructura / umbral / evidencia | Criterio binario | Vínculo con Secciones 1 y 2 |
| --- | --- | --- | --- | --- |
| **Entrada (Datos)** | El prototipo recibe e interpreta el archivo de carga del dataset cerrado. | Archivo CSV de 4,500 filas y 8 columnas (50 productos × 90 días). Al leerlo muestra en pantalla y en el log local: «4,500 registros cargados correctamente (50 productos, 90 días)». | **Funciona** si se leen y guardan en SQLite el 100% de las filas (4,500), con 0 errores de esquema y 0 nulos, 50 productos, 90 fechas y la distribución de cuadrantes 10 / 15 / 10 / 15. **No funciona** si falta o sobra una fila o aparece un error. | Sección 1-B (dataset cerrado y SQLite); Sección 2, paso 2 (backend guarda en `zenith.db`). |
| **Procesamiento (Lógica)** | La inferencia del TFT local sobre los 50 productos se ejecuta dentro de un límite de tiempo. | **Umbral: menos de 1,000 ms** por inferencia de los 50 productos, con el modelo ya cargado en memoria. Medición con `time.perf_counter()` antes y después de `predecir()`; la interfaz muestra «Inferencia: X ms» y el mismo valor queda en el log. | **Cumple** si el tiempo mostrado en la demostración es menor a 1,000 ms. **No cumple** si es igual o mayor. | Sección 1 (mismo algoritmo, solo 50 productos, CPU); Sección 2, paso 3 (la IA interviene al pulsar «Predecir desabasto»). |
| **Salida (UI/UX)** | La interfaz evidencia visualmente que la lógica funcionó. | En la tabla de 50 filas, la celda de cada producto con probabilidad de desabasto ≥ 0.50 se pinta de **rojo** y aparece un distintivo «Reabasto sugerido» con su orden en estado «pendiente». **Detonante:** pulsar «Predecir desabasto» con la fecha de corte de la demostración. | **Funciona** si, al terminar la inferencia y sin recargar la página, aparecen celdas rojas solo en los productos que de verdad quedan en cero existencia en los 7 días siguientes, y la tabla tiene exactamente 50 filas. **No funciona** en caso contrario. | Sección 1 (50 filas, cuadrantes de Kraljic); Sección 2, pasos 4 y 5 (salida con celdas rojas y orden sugerida con aprobación humana). |

### Notas por hito
- **Umbral de 1,000 ms: estimado, no medido.** No se pudo cronometrar el TFT en una laptop real. Antes de entregar, en la laptop más lenta del equipo, ejecuta la inferencia 30 veces y toma el percentil 95. Si el doble de ese valor es menor a 1,000 ms, se puede bajar el umbral (más estricto); **nunca subirlo**. Se mide solo la inferencia por lote; el arranque de PyTorch y la carga del checkpoint ocurren una vez y se reportan aparte. Si el checkpoint no está disponible o falla la inferencia, el hito no se cumple; no se admiten predicciones de respaldo o simuladas.
- **Fecha de corte de la demostración: 2026-10-22.** Cae dentro de los últimos 27 días, fuera del entrenamiento. En los 7 días siguientes entran en quiebre seis productos que cubren los cuatro cuadrantes de Kraljic: Insulina glargina y Losartán 50 mg (Estratégico), Paracetamol 500 mg (Apalancamiento), Vacuna influenza y Antigripal sobres (Cuello de botella) y Alcohol 70% (No crítico). Si el equipo la cambia, hay que recalcular qué productos deben salir rojos.
- **Métrica de calidad complementaria (no es un hito):** F1-Score de la alerta a 7 días, calculado con 21 cortes rodantes (2026-10-16 a 2026-11-05) cuyos horizontes completos caen dentro de los últimos 27 días (50 productos × 21 cortes = 1,050 casos). Se reporta el valor real junto con el número de positivos, aunque sea menor a la meta de 0.80 del piloto.

## 2. Guion de demostración en aula (unos 3 minutos)
1. **Preparación (antes de la clase).** Sin internet. Verificar la huella del CSV con `sha256sum data/ventas.csv`. En una terminal desde la raíz, iniciar `python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000`; en otra, desde `OpenJarvis\frontend`, ejecutar `npm run dev -- --host 127.0.0.1`. Abrir `http://127.0.0.1:5173/zenit`. El cronómetro es el contador «Inferencia: X ms» de la interfaz, respaldado por el log local.
2. **Carga (Hito de Entrada).** Cargar `ventas.csv`. Se ve el mensaje «4,500 registros cargados correctamente (50 productos, 90 días)». Resultado esperado: funciona.
3. **Ejecución (Hito de Procesamiento).** Fijar la fecha de corte 2026-10-22 y pulsar «Predecir desabasto». Se ve el tiempo «Inferencia: X ms». Resultado esperado: X menor a 1,000.
4. **Evidencia visual (Hito de Salida).** Al terminar, sin recargar, la tabla de 50 filas muestra celdas rojas solo en productos cuya probabilidad TFT sea ≥ 0.50. En la fecha de corte fijada, se comprueba la salida contra los seis productos que realmente llegan a existencia cero en los siete días siguientes.
5. **Aprobación.** Aprobar la orden de Losartán 50 mg (Estratégico): su estado cambia de «pendiente» a «aprobada».

## 3. Rúbrica de evaluación (informativa para el equipo)
| Criterio | Qué se espera | Peso |
| --- | --- | --- |
| Lógica de reducción de escala y frugalidad | Coherencia entre el escenario real (Sección 1-A) y el prototipo (Sección 1-B), y costo de 0.00 MXN explícito (Sección 2). | 40% |
| Claridad técnica del pipeline | Cómo se comunican en secuencia el frontend, el backend local y la lógica de IA (Sección 2). | 30% |
| Precisión de los hitos demostrables | Entrada, Procesamiento y Salida son medibles, binarios y verificables en vivo. | 30% |

Los pesos son los de la rúbrica del formato oficial de la Actividad 3.

## Estado de validación local

Medición del 21 de noviembre de 2026 (CPU AMD64, PyTorch CPU limitado a 1 hilo intraoperatorio y 1 interoperativo) tras reconstruir `OpenJarvis/modelo/` con variables puramente causales derivadas de las 8 columnas canónicas (`existencia_relativa`, `dias_cobertura`, `dias_sin_resurtido`, `es_quincena`), encoder fijo de 28 días, sin `producto` en `static_categoricals` ni `time_idx` absoluto en el decoder, y optimizador `Adam` (`lr=0.005`, `batch_size=128`, 45 épocas, `hidden_size=16`, `peso_positivo=156.5` calculado únicamente en los primeros 63 días):

- Pruebas automatizadas (`python -m pytest -q --noconftest tests\zenit`): **25 passed, 0 failed**.
- Inicialización del dataset y carga del checkpoint: **560.43 ms**, fuera del tiempo de inferencia.
- Inferencia TFT (30 lotes de 50 productos tras 1 calentamiento): mediana **72.64 ms**, p95 **85.57 ms** (`< 1,000 ms`: **cumple** en este equipo).
- Llamada completa (preparación del lote y TFT): mediana **120.95 ms**, p95 **176.62 ms**.
- Uso promedio del proceso durante las 30 llamadas: **0.97 núcleos equivalentes**.
- Evaluación rodante de los últimos 27 días (21 cortes × 50 productos = 1,050 casos, 70 positivos reales): **TP = 32, FP = 7, FN = 38, TN = 973** → **Precision = 0.8205**, **Recall = 0.4571**, **F1 = 0.5872** (sube desde `0.0000`).
- Fecha de demo `2026-10-22`: el TFT emitió **2 alertas verdaderas (`≥ 0.50`) y 0 falsos positivos** — **Insulina glargina** (`1.0000`, Estratégico) y **Vacuna influenza** (`0.9799`, Cuello de botella, que no tuvo quiebres en entrenamiento), con **Losartán 50 mg** en `0.3672` (tercer riesgo más alto). Los otros tres productos que quiebran en los 7 días siguientes (*Paracetamol 500 mg*, *Antigripal sobres* y *Alcohol 70%*) aún estaban en los días 4 a 6 de su ciclo semanal normal el `2026-10-22` (su primer resurtido fallido ocurre después del corte), por lo que el Hito de Salida estricto (6 de 6 en esa fecha) sigue **parcial** y no se maquilla bajando el umbral.

Medición adicional del 18 de noviembre de 2026 en la misma laptop Intel Core i5-1235U (10 núcleos físicos y 12 lógicos), con PyTorch limitado a un hilo intraoperatorio y uno interoperativo. Se usó `python -m modelo.medir_rendimiento`, con una pasada de calentamiento y 30 lotes de 50 productos:

- Inicialización del dataset y carga del checkpoint: **2,344.33 ms**, fuera del tiempo de inferencia.
- Inferencia TFT: mediana **214.19 ms**, p95 **240.44 ms**.
- Llamada completa (preparación del lote y TFT): mediana **406.86 ms**, p95 **509.20 ms**.
- Uso promedio del proceso durante las 30 llamadas: **0.95 núcleos equivalentes**; esta cifra es promedio, no un límite térmico del equipo.

El hito de procesamiento queda por debajo de 1,000 ms en esta laptop. Esta corrida es más lenta que la medición del 17 de noviembre registrada abajo; no se atribuye la diferencia a una causa sin controlar las condiciones de energía, temperatura y carga. Se conserva la medición nueva y debe repetirse en la laptop más lenta, idealmente la de 3 núcleos. Limitar los hilos de PyTorch reduce su contención, pero no garantiza una temperatura específica ni limita otros procesos del sistema.

Medición del 17 de noviembre de 2026 en una laptop con Intel Core i5-1235U (10 núcleos físicos y 12 lógicos), con el modelo cargado y 50 productos:

- El PyTorch predeterminado usaba 10 hilos; antes del límite, la comparación corta ocupó en promedio 9.24 núcleos equivalentes. Con un hilo, la ocupación bajó a 0.96 núcleos equivalentes y la mediana de inferencia bajó de 88.79 ms a 64.36 ms.
- Inferencia TFT con un hilo: 30 repeticiones, p95 de **69.60 ms** y mediana de **60.98 ms**. El p95 de la llamada completa fue 149.25 ms; incluye preparación del lote, pero no la carga inicial del checkpoint.
- La probabilidad máxima cambió solo 4.3×10⁻¹⁰ al comparar 10 y 1 hilo; la cantidad de alertas se mantuvo igual.
- F1 rodante: **0.0000**; 70 positivos reales de 1,050 casos. El checkpoint no emitió alertas con probabilidad ≥ 0.50.
- Fecha de demo 2026-10-22: el modelo emitió 0 alertas, mientras que los datos contienen 6 productos con existencia cero en los siete días siguientes.

Por lo tanto, el Hito de Procesamiento cumple en esta laptop; aún debe repetirse en la laptop más lenta del equipo. El Hito de Salida **no está cumplido**. No se deben agregar alertas prefabricadas ni bajar el umbral para aparentar cumplimiento.

## 4. Declaración de coherencia (texto para el reporte)
«Los tres hitos de validación usan exactamente los elementos comprometidos en las Secciones 1 y 2: el dataset cerrado de 50 productos y 90 días (4,500 registros, verificado con su huella SHA-256), el Temporal Fusion Transformer local en CPU como algoritmo, y la misma regla de alerta con umbral de probabilidad de 0.50. No se introducen datos ni métricas nuevas. Todos los hitos se demuestran en una computadora personal común, sin red externa ni servidores, con herramientas gratuitas (Python, SQLite, `time.perf_counter()` y la propia interfaz), por lo que el costo se mantiene en 0.00 MXN. Cada hito se expresa como funciona o no funciona con evidencia observable en pantalla.»

## Reglas para la IA que construye esto
- No cambies el dataset, la fecha de corte, el umbral de 0.50 ni el umbral de milisegundos sin avisar y sin actualizar este archivo.
- Cada hito debe poder comprobarse con un comando o una acción visible, no con una opinión.
- La interfaz debe mostrar el conteo de carga, el tiempo de inferencia y las celdas rojas sin recargar la página.
- Una falla del TFT debe mostrarse como error y no como una predicción exitosa, un tiempo de inferencia válido o datos de respaldo.
- Si no logras cumplir un hito, repórtalo; no lo maquilles con datos precargados.
