# Acción ZENIT: Recepción de Mercancía y Actualización de Existencias (nueva)

Cierra el ciclo del desabasto: cuando llega el pedido, la existencia sube y el riesgo baja.

---

## 1. Propósito
Registrar qué llegó de una orden `emitida`, verificarlo y actualizar la existencia vigente **sin tocar** la tabla canónica `ventas`.

## 2. Flujo
```
[ Orden emitida ] ─► [ Inspección física ] ─► [ Registro de la recepción ] ─► [ movimientos_inventario ]
                              │                                                       │
                       rechazo o cuarentena                                           ▼
                                                              [ Existencia vigente ↑  →  riesgo ↓ ]
```

## 3. Datos que se capturan (los captura una persona)
Orden, cantidad recibida, fecha de caducidad del lote, temperatura al recibir (solo productos con `requiere_refrigeracion = 1`), comprobante (factura o remisión) y notas.

## 4. Reglas de aceptación
- **Cantidad:** se acepta lo recibido. Si es menor a lo pedido, la orden pasa a `recibida_parcial` y el faltante queda visible.
- **Caducidad:** si el tiempo restante es menor a la caducidad mínima (propuesta: 90 días), se marca para revisión del encargado.
- **Cadena de frío:** para productos refrigerados la temperatura registrada debe estar entre 2 y 8 °C; fuera de ese rango el lote queda en **cuarentena** y no suma a la existencia.
- **Comprobante:** se guarda en una carpeta local; se registra su ruta y su SHA-256, nada se sube a la nube.

## 5. Existencia vigente
`ventas` no cambia. Cada entrada se guarda en `movimientos_inventario` y la existencia vigente es:

$$\text{Existencia vigente} = \text{existencia en la fecha de corte} + \sum \text{entradas posteriores} - \sum \text{salidas posteriores}$$

## 6. Después de recibir
- Cada recepción aceptada crea un **lote** en `lotes` con su caducidad, base de la rotación FEFO (ver caducidad y merma).
- La orden pasa a `recibida` (o `recibida_parcial`) y luego `cerrada`; el comprobante entra a la conciliación.
- La siguiente inferencia usa la nueva existencia.
- Se calcula el **cumplimiento del proveedor** (cantidad recibida ÷ pedida) y el tiempo de entrega, que alimentan la verificación de proveedor.

## 7. API
`POST /api/zenit/recepciones`. Rechaza (422) una recepción sin orden `emitida` o sin usuario.

## 8. Cómo se verifica
Una recepción parcial deja la orden en `recibida_parcial`; un refrigerado a 12 °C no suma existencia; `ventas` sigue teniendo 4,500 filas y la misma huella.
