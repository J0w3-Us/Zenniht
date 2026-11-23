# Acción ZENIT: Carga y Validación del Dataset Canónico

Primer paso de **ZENIT | Farmacia La Esperanza**: ingerir y verificar localmente el historial de ventas y existencias.

---

## 1. Propósito y alcance

Cargar `data/ventas.csv` en la tabla `ventas` de SQLite (`zenith.db`) con consistencia verificada y sin errores de esquema. Es el **Hito de Entrada**. El dataset es cerrado (50 productos × 90 días) y, una vez cargado, no se modifica.

**Entrada:** archivo CSV. **Salida:** tabla `ventas` con 4,500 filas, o rechazo completo con el motivo.

---

## 2. Flujo

```
[ ventas.csv ] ─► [ Validaciones en orden ] ─► [ Transacción única en SQLite ] ─► [ Mensaje ]
                         │ falla alguna                    │ falla algo
                         ▼                                 ▼
              [ Rechazo con motivo; la base queda intacta ]  [ ROLLBACK ]
```

---

## 3. Validaciones (en este orden; se detiene en la primera que falla)

1. **Archivo:** existe, es UTF-8 y pesa menos de 2 MB (valor de sanidad; el CSV oficial pesa cerca de 300 KB).
2. **Encabezado:** exactamente `producto, fecha, unidades_vendidas, existencia, cuadrante_kraljic, requiere_refrigeracion, fecha_caducidad, temperatura`, en ese orden.
3. **Tamaño:** 4,500 filas, 0 celdas vacías.
4. **Tipos y rangos:** fechas ISO válidas; `unidades_vendidas` y `existencia` enteros mayores o iguales a 0; `requiere_refrigeracion` solo 0 o 1; `temperatura` numérica; `cuadrante_kraljic` uno de los cuatro valores.
5. **Estructura:** clave `(producto, fecha)` única; 50 productos, cada uno con 90 fechas consecutivas.
6. **Distribución Kraljic:** Estratégico 10, Apalancamiento 15, Cuello de botella 10, No crítico 15.
7. **Consistencia de inventario:** para cada producto y día, `existencia_t + unidades_vendidas_t ≥ existencia_{t-1}`. La diferencia es el resurtido implícito y nunca puede ser negativa.
8. **Caducidad:** `fecha_caducidad` constante por producto y posterior a la última fecha del archivo.
9. **Huella:** SHA-256 igual a `1826980b24abea8784d6ba63c7f05f3b3aa9b434632bc976e7627ceb2ea43f7b`.

**Si la huella no coincide** (pero las demás pasan): la carga se permite en **modo exploración**, la base se marca `canonico = 0` y el sistema bloquea la verificación de hitos. En **modo evaluación** (el de la demostración) se rechaza.

---

## 4. Persistencia

- Una sola transacción (`BEGIN IMMEDIATE`): vaciar `ventas`, insertar las 4,500 filas, confirmar.
- **Idempotente:** cargar dos veces el mismo archivo deja el mismo resultado; nunca duplica.
- Si algo falla, `ROLLBACK` y la base conserva su estado anterior.
- Se registra el evento en `bitacora` (resultado, huella, fecha UTC).

## 4 bis. Lotes y datos complementarios
- Tras cargar `ventas`, se crean 50 filas en `lotes` (un lote por producto) con la `fecha_caducidad` del dataset. Es la base de las acciones de caducidad y de recepción.
- Los precios, proveedores y comprobantes son datos **complementarios**: se cargan aparte y no cambian la huella ni las 4,500 filas.

## 5. Cortes de datos
- **Último día con datos:** el máximo de `fecha` (2026-11-12).
- **Fecha de corte operativa:** la elige el operador (demostración oficial: 2026-10-22). Rango válido: 2026-09-11 a 2026-11-05, para tener 28 días de historia y 7 días futuros verificables.
- **Existencia vigente:** existencia de `ventas` en la fecha de corte más lo registrado en `movimientos_inventario` después de ella.

## 6. Respuestas
- Éxito: *«4,500 registros cargados correctamente (50 productos, 90 días)»* y el conteo en pantalla.
- Error: *«Carga rechazada: <motivo>. No se modificó la base.»* con hasta 5 detalles (fila y columna).

## 7. Cómo se verifica
`pytest -q tests/test_seccion1.py`; cargar un CSV con una columna menos y comprobar el rechazo sin cambios en la base; cargar dos veces y comprobar que siguen siendo 4,500 filas.
