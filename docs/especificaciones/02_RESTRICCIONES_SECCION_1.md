# Restricciones de la Sección 1 que heredan los hitos de la Sección 3

Estas restricciones son límites funcionales del prototipo, no metas de escala. No se amplía el conjunto de datos ni se agregan capacidades para otros giros.

1. **Universo cerrado:** una farmacia ficticia, La Esperanza; exactamente 50 productos, 90 días y 4,500 filas. `data/ventas.csv` debe tener solo las ocho columnas acordadas: `producto, fecha, unidades_vendidas, existencia, cuadrante_kraljic, requiere_refrigeracion, fecha_caducidad, temperatura`. La distribución de productos es Estratégico (10), Apalancamiento (15), Cuello de botella (10) y No crítico (15).
2. **Límite temporal:** los primeros 63 días se usan para entrenar y los últimos 27 para evaluación. Toda métrica se calcula sobre esos mismos 50 productos y únicamente en el periodo de evaluación; no se agregan productos, fechas ni sucursales.
3. **Único modelo:** Temporal Fusion Transformer de `pytorch-forecasting`, `hidden_size=16`, horizonte de 7 días, ejecutado localmente en CPU. El objetivo diario es `existencia = 0`; corrige las probabilidades por la ponderación de clases y calcula el riesgo semanal como `1 - producto(1 - p_diaria)` para los siete pasos, suponiendo independencia entre días. No se admiten LLM, APIs, reglas sustitutas ni predicciones prefabricadas como resultado del modelo.
4. **Fallo explícito:** si falta el checkpoint, el modelo no puede cargarse o la inferencia falla, se informa el error y no se devuelve un JSON de respaldo, un valor por defecto ni una predicción sintética. Ese intento no cuenta para los hitos ni para el tiempo de inferencia.
5. **Límite de alerta:** una probabilidad TFT ≥ 0.50 marca la alerta visual. Kraljic solo ordena la prioridad; no cambia probabilidades, etiquetas ni el umbral.
6. **Órdenes:** solo se generan sugerencias para revisión. Aprobar requiere una acción explícita de la persona usuaria; el sistema no compra, paga, contacta proveedores ni ejecuta órdenes. No se calcula ni inventa cantidad sugerida mientras no exista una regla de reabasto acordada.
7. **Interfaz:** la tabla contiene exactamente los 50 productos. El rojo se aplica según la regla de alerta acordada y se valida contra las existencias reales de los siete días siguientes a la fecha de corte.
8. **Costo y ejecución local:** costo de operación 0.00 MXN; sin APIs gratuitas o de pago, nube, servicios externos, telemetría ni tráfico de red requerido. Las dependencias se preparan antes de la demostración; el prototipo debe funcionar sin Internet.
9. **Fuera de alcance:** recetas, pacientes, diagnóstico, cadena de frío con sensores (solo se conserva `requiere_refrigeracion`), más farmacias o sucursales, chat generativo y cualquier función no relacionada con predicción de desabasto y aprobación manual de reabasto.

## Verificación automática
`tests/test_seccion1.py` comprueba columnas, 4,500 filas, 50 productos, 90 fechas, la distribución 10/15/10/15 de Kraljic, ausencia de nulos y al menos 5 productos con quiebre en los últimos 27 días.
Ejecutar: `python data/generar_datos.py && pytest -q`.

## Notas sobre los datos generados
- Siete productos tienen interrupciones de surtido en una ventana temprana y otra tardía, para que el modelo vea quiebres al entrenar y al evaluarse.
- Los quiebres son pocos: cerca de 1.6% de las ventanas de entrenamiento y 6.6% de las de prueba son positivas. Con tan pocos positivos el F1-Score es sensible; usa el ponderado de clases al entrenar y reporta cuántos positivos hay.
