# Acción ZENIT: Verificación de Hitos de Validación (nueva)

Un diagnóstico automático que dice, antes de la clase, si los tres hitos de la Sección 3 pasan.

---

## 1. Propósito
Ensayar la demostración sin depender de la memoria: un comando o una ruta (`GET /api/zenit/verificacion/hitos`) que imprime **PASA** o **FALLA** por hito.

## 2. Flujo
```
[ Huella y pruebas ] ─► [ Hito de Entrada ] ─► [ Hito de Procesamiento ] ─► [ Hito de Salida ] ─► [ Informe ]
```

## 3. Qué comprueba
1. **Preparación:** huella SHA-256 del CSV, sin conexión a internet, versiones de Python y PyTorch, `modelo_version`.
2. **Entrada:** carga en una base temporal; 4,500 filas, 50 productos, 90 fechas, 0 errores, 0 nulos, distribución 10/15/10/15, mensaje esperado.
3. **Procesamiento:** una inferencia de calentamiento descartada, 30 corridas con `time.perf_counter()` y 1 hilo; informa mínimo, mediana, percentil 95 y máximo. **PASA** si el tiempo de la corrida de demostración es menor al umbral (1,000 ms, estimado).
4. **Salida:** fecha de corte 2026-10-22; la tabla tiene 50 filas; calcula qué productos salen en rojo y los compara con los que de verdad quedan en cero existencia en los 7 días siguientes.
   - **PASA** si todo producto en rojo es un quiebre real (precisión de 100 %).
   - Informa además el recall y los productos esperados (Losartán, Paracetamol, Vacuna influenza, Antigripal sobres y Alcohol 70 %) para que el equipo vea qué detectó el modelo.
5. **Aprobación:** crea una orden de prueba, la aprueba con un usuario y comprueba el cambio de estado; luego borra la base temporal.

## 4. Informe
Tabla con hito, resultado, valor medido, umbral y la fecha; el código de salida del comando es distinto de cero si algo falla, para usarlo también en GitHub Actions.

## 5. Advertencias
- Un solo falso positivo en la fecha de demostración reprueba el Hito de Salida (decisión D4).
- El modo respaldo no cuenta para el Hito de Procesamiento.
- Todo es gratuito y local.
- Los módulos de caducidad, cadena de frío y comprobantes tienen sus propias pruebas, pero no forman parte de los tres hitos de la Sección 3.

## 6. Cómo se verifica
Con un CSV alterado, la preparación y la entrada fallan; con el umbral puesto en 1 ms, el Hito de Procesamiento falla; sin modelo, la verificación informa el error y no inventa un resultado.
