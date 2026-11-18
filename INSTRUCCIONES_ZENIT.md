# Instrucciones del prototipo ZENIT

Este archivo define el alcance que deben respetar quienes desarrollen o ejecuten
ZENIT dentro de OpenJarvis. El TFT no recibe un prompt conversacional: sus
restricciones se aplican en el código de datos, entrenamiento e inferencia.

## Modelo de predicción

- Único modelo: Temporal Fusion Transformer de `pytorch-forecasting`.
- `hidden_size=16`, entrenamiento e inferencia en CPU, horizonte de siete días.
- Entrenar con los primeros 63 días del dataset canónico; evaluar solo los
  últimos 27 días, con las 50 series de productos y los 21 cortes rodantes.
- Objetivo diario: `existencia == 0`. Entrenar con el peso positivo
  `negativos / positivos` calculado únicamente en el bloque de entrenamiento.
- Corregir la probabilidad por el peso de clase antes de agregar el riesgo
  semanal: `1 - producto(1 - p_diaria)`, suponiendo independencia entre días.
- El umbral visual de alerta es `0.50`. Kraljic solo prioriza el orden y no
  altera probabilidades ni etiquetas.

## Datos y límites funcionales

- Usar exclusivamente `data/ventas.csv`: 1 farmacia ficticia, 50 productos,
  90 días, 4,500 filas y sus ocho columnas acordadas.
- Mantener almacenamiento local en SQLite y ejecución sin Internet, APIs,
  servicios remotos, telemetría ni descarga de modelos durante la ejecución.
- No sustituir el TFT por un LLM, una regla, un resultado prefabricado o una
  respuesta de respaldo. Si falta o falla el checkpoint, mostrar el error.
- Las órdenes son sugerencias locales: cantidad sin definir y aprobación humana
  explícita. No automatizar compras, pagos ni contacto con proveedores.
- Mantener fuera recetas, pacientes, diagnóstico, sensores IoT y sucursales
  adicionales.

## Operación local

Desde la raíz de este repositorio:

```powershell
python data\generar_datos.py
python -m modelo.entrenar_tft
python -m pytest -q tests\zenit
```

El entrenamiento escribe `modelo/zenith_tft.ckpt`. La API local carga el
checkpoint al ejecutar una predicción; para probarla, iniciar
`python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000`.
La medición de inferencia excluye la carga inicial del checkpoint.
