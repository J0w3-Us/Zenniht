# Entrenamiento y validación del TFT

Actualizado el 23 de noviembre de 2026. Este flujo implementado sustituye las
descripciones anteriores de entrenamiento sin validación y de riesgo diario
independiente. Configurar Ollama con un prompt sigue siendo configuración del
asistente; no entrena el pronóstico.

## Separación temporal

Para el historial canónico de 90 días, los índices se cuentan desde cero:

| Uso | Etiquetas | Propósito |
| --- | --- | --- |
| Ajuste | 0 a 48 | Aprender pesos y ajustar normalizadores |
| Validación | 49 a 62 | Seleccionar época y detener entrenamiento |
| Prueba | 63 a 89 | Reportar calidad final; no elegir parámetros |

Cada ventana conserva 28 días de historia y siete futuros completos. La
validación reutiliza historia anterior, pero ninguna de sus etiquetas aparece
en ajuste. Los normalizadores se guardan y recuperan del checkpoint.

## Objetivo y selección

El TFT aprende directamente si existe al menos un día sin stock en el horizonte.
La pérdida es entropía cruzada semanal ponderada; promedia los siete logits
antes de softmax y compara con el máximo de las siete etiquetas observadas.
La corrección por peso positivo se aplica una sola vez al riesgo semanal.
No produce probabilidades diarias ni supone independencia entre días.
Kraljic ordena la presentación y no entra al nuevo modelo.

Se guarda el checkpoint de menor `val_loss`, con parada temprana de paciencia
ocho y `min_delta=0.0001`. Las curvas CSV, semilla, parámetros, versiones,
huella SHA-256 del CSV y del checkpoint quedan junto a cada candidata. El
ajuste de hiperparámetros debe usar exclusivamente validación.

## Comandos

Ejecutar dentro de `OpenJarvis/`, con el entorno preparado:

```powershell
.\.venv\Scripts\python.exe -m modelo.entrenar_tft tft --epochs 60 --evaluar
```

La salida indica la ruta real `modelo/versiones/<version>/mejor.ckpt`.
`--ckpt` selecciona el directorio base de salida, no sobrescribe ese archivo.
El checkpoint activo `modelo/zenith_tft.ckpt` permanece intacto.

La evaluación usa exactamente el CSV y checkpoint de esa candidata. Un fallo
sale como error, no como éxito sin métricas. Se genera `mejor.evaluacion.json`.

`--activar` permite sustituir el modelo activo únicamente si la validación
alcanza F1 >= 0.75 con al menos diez ventanas positivas; se comprueban las
huellas y se conserva un respaldo del anterior. Diez positivos son una
salvaguarda operativa, no una garantía de significancia estadística. Las
ventanas solapadas no son observaciones independientes. La meta F1 de 0.80
sigue siendo una meta, no un resultado garantizado.

## Evaluación y trazabilidad

El reporte incluye matriz de confusión, precisión, recall, F1 al umbral fijo
0.50, Brier, average precision (`pr_auc`), intervalos de calibración, detalle
por producto y referencia de cobertura menor a siete días. Registra episodios
que comienzan durante el periodo y anticipación de sus alertas; no cuenta un
quiebre iniciado antes como episodio nuevo.

La API ofrece `POST /api/zenit/evaluar` para medir el modelo activo sin
reentrenarlo y `GET /api/zenit/evaluacion` para recuperar la última medición,
identificada por versión. Después de cambiar código, reiniciar la API local.
El cambio de checkpoint se detecta por la caché en nuevas solicitudes.

`predicciones` conserva la vista actual; `predicciones_historico` agrega cada
inferencia con corte, versión, objetivo y huella. `evaluaciones` conserva los
reportes solicitados desde la API. No hay reentrenamiento automático ni se
usan las aprobaciones como etiquetas. Falta incorporar datos operativos de
entregas, solicitudes no atendidas y decisiones de reabasto para evaluar el
efecto de intervenciones humanas.

Los checkpoints antiguos se pueden leer, pero se identifican como `diario_legacy`
y emiten una advertencia sobre su agregación aproximada. Nunca se reinterpretan
silenciosamente como modelos semanales nuevos.

## Resultado de la revisión

La candidata `20261123T221906795696Z` terminó tras 16 épocas ejecutadas y
seleccionó un checkpoint con `val_loss=0.332583`. Hubo 750 ventanas de ajuste
(21 positivas) y 400 de validación (solo tres positivas). Su F1 de validación
fue 0, por lo que quedó rechazada. La prueba final de auditoría dio:

| Modelo | Precisión | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Anterior | 0.8205 | 0.4571 | 0.5872 | 32 | 7 | 38 |
| Candidata semanal | 0.6078 | 0.4429 | 0.5124 | 31 | 20 | 39 |

Esta prueba se reportó después del rechazo y no se usó para ajustar la
candidata. El modelo anterior sigue activo. El proceso de entrenamiento es
ahora verificable, pero no se ha demostrado una mejora predictiva. La siguiente
iteración necesita más episodios independientes y señales de suministro
disponibles antes de predecir; no mover las fechas para mejorar artificialmente
las métricas ni reutilizar la prueba para seleccionar parámetros.
