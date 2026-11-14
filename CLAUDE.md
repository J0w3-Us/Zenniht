# ZENIT: prototipo a escala (Actividad 3, Sección 1)

Eres el asistente de desarrollo del prototipo de ZENIT. Lee este archivo completo y los documentos de `docs/` antes de escribir código. Responde en español.

## Qué es ZENIT
Sistema de IA que predice el **desabasto de medicamentos e insumos en farmacias de barrio** y sugiere órdenes de compra que el dueño aprueba. **Solo desabasto**: no agregues funciones de otros giros ni de otros problemas.

## Qué estamos construyendo
Un prototipo local que parte del repositorio **Open-Jarbis** (ya en en la carpeta de ZENIT), sin las modificado para cumplir las restricciones de ZENIT y de la actividad. Jarbis aporta la carcasa (estructura, interfaz, backend); ZENIT aporta los datos y el modelo.

## Restricciones obligatorias (no se negocian)
1. **Universo cerrado:** 1 farmacia ficticia (Nombre La Esperanza), 50 productos, 90 días, 4,500 filas. Nada de más productos, sucursales ni días.
2. **Costo cero:** sin APIs de pago, sin nube, sin servidores externos, sin licencias comerciales. Solo software libre.
3. **Local y sin internet:** debe correr fluido en una computadora personal común durante la clase, sin configuración de red.
4. **Mismo algoritmo que el escenario real:** Temporal Fusion Transformer (TFT) con `pytorch-forecasting`, `hidden_size` 16, en CPU, horizonte de 7 días. No lo reemplaces por otro modelo ni por una API.
5. **Mismos datos que la Sección 3:** toda métrica o hito usa solo esos 50 productos. La evaluación (F1-Score de la alerta de desabasto a 7 días) usa los **últimos 27 días**.
6. **Recetas, sensores de frío y múltiples sucursales quedan fuera.** La cadena de frío es solo la columna `requiere_refrigeracion`.

Si una petición contradice una restricción, avisa antes de implementarla y propón una alternativa que sí la cumpla.

## Datos
Columnas exactas de `data/ventas.csv`: `producto, fecha, unidades_vendidas, existencia, cuadrante_kraljic, requiere_refrigeracion, fecha_caducidad, temperatura`.
Cuadrantes de Kraljic: Estratégico (10), Apalancamiento (15), Cuello de botella (10), No crítico (15).
Se generan con `python data/generar_datos.py` (semilla fija). Etiqueta del modelo: «existencia = 0 en alguno de los próximos 7 días».

## Estructura objetivo
```
data/generar_datos.py   modelo/entrenar_tft.py   modelo/predecir.py
kraljic.py              db.py (SQLite)           tests/
(backend y UI de Jarbis, adaptados)
```

## Cómo trabajar en Jarbis
- **Antes de modificar nada**, inventaría el repo y escribe `docs/JARBIS_INVENTARIO.md` (ver `docs/03_PLAN_DE_ARMADO.md`).
- Conserva el archivo de licencia de Jarbis y respeta sus condiciones.
- Quita llamadas a APIs de pago o en la nube y claves del `.env`. Nunca subas claves ni el `.env` a Git.
- Haz cambios pequeños, uno por paso del plan, y corre `pytest -q` después de cada uno.

## Definición de terminado (por hito)
- **Entrada:** el sistema carga `data/ventas.csv` (4,500 filas) sin errores.
- **Procesamiento:** la inferencia del TFT local sobre los 50 productos se mide en milisegundos. El umbral lo define el equipo en la Sección 3; no lo inventes.
- **Salida:** la tabla muestra exactamente 50 filas y pinta de rojo los productos en desabasto.

## Estilo
Python, comentarios y mensajes en español, funciones cortas, nada de dependencias que no estén en `requirements.txt`.
