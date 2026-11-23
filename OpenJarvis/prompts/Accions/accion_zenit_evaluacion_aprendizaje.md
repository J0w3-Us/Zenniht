# Acción ZENIT: Evaluación y Aprendizaje del Modelo (nueva)

Es la Torre de Aprendizaje: compara cada predicción con lo que pasó y decide si el modelo sigue sirviendo.

---

## 1. Propósito
Medir la calidad del TFT con datos reales del dataset y detectar cuándo conviene reentrenar.

## 2. Flujo
```
[ Predicciones guardadas ] ─► [ Existencia real de los 7 días siguientes ] ─► [ Matriz de confusión ]
                                                                                     │
[ Alerta de deriva / reentrenamiento programado ] ◄─ [ F1, precisión, recall, calibración ]
```

## 3. Qué se compara
- **Real:** hubo al menos un día con existencia = 0 en los 7 días siguientes a la fecha de corte.
- **Predicho:** riesgo semanal ≥ 0.50.
- **Ventana de evaluación:** solo los últimos 27 días del dataset (fechas de corte 2026-10-17 a 2026-11-05, que tienen 7 días futuros completos).

## 4. Métricas
Verdaderos y falsos positivos y negativos; precisión, recall y **F1-Score** al umbral 0.50; número de positivos (se reporta siempre); error de Brier y calibración en pocos intervalos. Meta del piloto: F1 de 0.80, que es una meta, no un resultado.

**Referencia:** se calcula también el F1 de una regla simple (cobertura menor a 7 días) solo para mostrar si el TFT aporta algo. No sustituye al modelo.

## 5. Deriva y reentrenamiento
- Si el F1 baja de **0.75** o cambia el catálogo de productos, ZENIT **solo emite una alerta** (exclusión 4 de la Sección 2).
- El reentrenamiento corre en la ventana programada del domingo por la noche, con validación del equipo.
- Cada checkpoint tiene `modelo_version` y la huella del dataset; el anterior se conserva para volver atrás. El checkpoint de la demostración nunca se sobrescribe.
- **Regla de validez:** no se reentrena con los últimos 27 días antes de reportar la evaluación; usarlos invalidaría las métricas.

## 6. Retroalimentación humana
Los descartes con motivo «error de predicción» se cuentan y se muestran junto a la evaluación como señal para revisar; no entrenan nada por sí solos.

## 7. Persistencia y API
Tabla `evaluaciones` (ventana, matriz, F1, positivos, fecha). `GET /api/zenit/evaluacion` devuelve la última.

## 8. Cómo se verifica
Con un conjunto sintético con respuesta conocida el F1 calculado coincide; la evaluación nunca incluye días de entrenamiento; con F1 de 0.70 aparece la alerta y no se reentrena sola.
