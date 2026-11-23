# Acción ZENIT: Pronóstico de Desabasto con IA (Inferencia TFT)

Ejecuta el modelo de series de tiempo que anticipa la falta de medicamentos e insumos.

---

## 1. Propósito y algoritmo

Estimar, para cada uno de los 50 productos, la probabilidad de que su existencia llegue a cero en los próximos 7 días con un **Temporal Fusion Transformer** (`pytorch-forecasting`, `hidden_size=16`, CPU local). Es el **Hito de Procesamiento**: la inferencia por lote de los 50 productos debe tardar **menos de 1,000 ms** (umbral estimado, por confirmar midiendo).

---

## 2. Flujo

```
[ Fecha de corte ] ─► [ Ventana de 28 días ] ─► [ Inferencia TFT (CPU, 1 hilo) ]
                                                          │
                                                          ▼
[ Alerta (riesgo ≥ 0.50) ] ◄─ [ Riesgo semanal ] ◄─ [ Riesgo diario, 7 pasos ]
        │
        └─► orden sugerida en estado «pendiente» (nunca aprobada por el sistema)
```

---

## 3. Qué significa «riesgo» (definición exacta)

- **Quiebre:** existencia = 0 al cierre de un día.
- **Riesgo semanal:** probabilidad de al menos un quiebre en los días t+1 a t+7.
- **Riesgo diario $h_t$:** probabilidad de que el **primer** quiebre ocurra el día t, dado que no hubo quiebre antes (riesgo instantáneo).

Con esa definición el riesgo semanal es exacto:

$$\text{Riesgo semanal} = 1 - \prod_{t=1}^{7} (1 - h_t)$$

> **Advertencia:** si el modelo entrega la probabilidad *marginal* de estar sin existencia el día t, esta fórmula **no** es válida: los quiebres persisten hasta el resurtido, no son independientes, y el producto sobrestima el riesgo. En ese caso se entrena el evento semanal directamente (un valor por producto) o se usa el máximo de las probabilidades diarias como cota inferior. La decisión D1 del archivo de análisis fija cuál se usa.

**Producto ya en quiebre en la fecha de corte:** riesgo semanal = 1.0 por definición, etiqueta `en_quiebre`, en rojo.

---

## 4. Variables de entrada

| Tipo | Variables |
| --- | --- |
| Pasado observado (ventana de 28 días) | `unidades_vendidas`, `existencia`, días de cobertura (existencia ÷ media móvil de 7 días de ventas, con protección contra división entre cero), resurtido implícito y días desde el último resurtido, `temperatura` observada |
| Futuro conocido | Día de la semana, día del mes, indicador de quincena (días 1, 15, 16 y 30) |
| Estáticas | `producto`, `requiere_refrigeracion` |

- **No** se usa la temperatura futura: no es conocida. Si algún día se incorpora un pronóstico del clima, se declara como variable distinta.
- El cuadrante de Kraljic **no** es entrada del modelo (ver D2): solo ordena la presentación.
- Nada posterior a la fecha de corte entra a la ventana.

---

## 5. Entrenamiento (referencia)
- Datos: días 1 a 63 (2026-08-15 a 2026-10-16). Los últimos 14 días de ese tramo sirven de validación para detener el entrenamiento.
- Ventanas de 28 días de historia y 7 de horizonte; semilla fija.
- Hay pocos positivos (cerca de 1.6 % de las ventanas): usar ponderación de clases y reportar el número de positivos.
- El checkpoint `modelo/zenith_tft.ckpt` guarda la huella del dataset y una versión (`modelo_version`).

## 6. Inferencia y medición
1. El modelo se carga **una vez** (no cuenta en el tiempo).
2. Se descarta una inferencia de calentamiento.
3. Con `torch.set_num_threads(1)` y `torch.inference_mode()`, se cronometra con `time.perf_counter()` desde la tabla de entrada de los 50 productos ya armada hasta tener los riesgos semanales. La preparación de datos se reporta aparte.
4. Para fijar el umbral: 30 corridas en la laptop más lenta, percentil 95.

## 7. Alertas y persistencia
- Riesgo ≥ 0.50 → celda roja y orden sugerida `pendiente`.
- Se crea la orden solo si el producto no tiene ya una orden `pendiente` o `aprobada` vigente (sin duplicados).
- Se guardan en `predicciones`: fecha de corte, riesgo semanal, riesgos diarios, `modelo_version` y milisegundos.
- Si el riesgo ya no justifica una orden `pendiente` antigua, esa orden pasa a `obsoleta`.

## 8. Fecha de corte
- Rango válido: 2026-09-11 a 2026-11-05. Fuera de él no hay 28 días de historia o no se pueden verificar los 7 días siguientes, y la interfaz lo avisa.
- Demostración oficial: 2026-10-22 (posterior al entrenamiento, sin fuga de datos).

## 9. Modo respaldo
Si la instalación falla en el aula, se muestra `predicciones_respaldo.json`, generado con este mismo modelo y marcado «modo respaldo». No sirve para medir el Hito de Procesamiento.

## 10. Calibración
Con pocos positivos, el 0.50 puede alcanzarse rara vez. Se reporta la calibración (riesgo previsto contra frecuencia observada en pocos intervalos) y el número de positivos. **El umbral no se modifica.**

## 11. Cómo se verifica
Medir 30 corridas; comprobar que 50 productos producen 50 riesgos entre 0 y 1; comprobar que una fecha fuera de rango se avisa; comprobar que dos corridas con la misma fecha no duplican órdenes.

## 12. Quién consume este módulo
- **Presupuesto y cotización:** el riesgo y la demanda definen qué se cotiza y cuánto.
- **Kraljic:** ordena las alertas que salen de aquí.
- **Caducidad y merma:** una orden sugerida muestra una advertencia si sumar su cantidad dejaría unidades en riesgo de vencer antes de venderse.
- **Copiloto Local:** responde preguntas con las predicciones guardadas.
