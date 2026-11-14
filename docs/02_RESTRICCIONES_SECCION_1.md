# Restricciones de la Sección 1 que heredan los hitos de la Sección 3

1. **Universo de datos:** solo 50 productos, 90 días y 4,500 filas. El archivo de carga del Hito de Entrada es `data/ventas.csv` con las 8 columnas definidas.
2. **Algoritmo:** el Hito de Procesamiento mide la inferencia del TFT local sobre esos 50 productos, en CPU. No se evalúa otra IA ni una API externa.
3. **Datos de evaluación:** cualquier métrica (F1-Score de la alerta de desabasto a 7 días) se calcula solo con los últimos 27 días de los 50 productos.
4. **Interfaz:** la tabla del Hito de Salida tiene exactamente 50 filas; la celda roja se demuestra con productos que el script dejó en quiebre.
5. **Costo cero y local:** la demostración corre en una computadora personal sin internet, servidores externos ni licencias de pago.

## Verificación automática
`tests/test_seccion1.py` comprueba columnas, 4,500 filas, 50 productos, 90 fechas, la distribución 10/15/10/15 de Kraljic, ausencia de nulos y al menos 5 productos con quiebre en los últimos 27 días.
Ejecutar: `python data/generar_datos.py && pytest -q`.

## Notas sobre los datos generados
- Siete productos tienen interrupciones de surtido en una ventana temprana y otra tardía, para que el modelo vea quiebres al entrenar y al evaluarse.
- Los quiebres son pocos: cerca de 1.6% de las ventanas de entrenamiento y 6.6% de las de prueba son positivas. Con tan pocos positivos el F1-Score es sensible; usa el ponderado de clases al entrenar y reporta cuántos positivos hay.
