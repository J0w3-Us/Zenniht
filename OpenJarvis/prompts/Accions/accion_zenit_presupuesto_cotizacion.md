# Acción ZENIT: Presupuestación y Cotización de Reabasto

Convierte las alertas de desabasto en presupuestos concretos en MXN.

---

## 1. Propósito
Decirle al encargado **cuánto pedir y cuánto costará** antes de aprobar. No compra nada.

---

## 2. Datos que usa
`catalogo_precios` es una tabla **complementaria y sintética** (precios ficticios, `es_sintetico = 1`), separada de `ventas`: no altera el dataset cerrado ni su huella SHA-256, y ningún hito la evalúa.

| Campo | Significado |
| --- | --- |
| `producto` | Uno de los 50 productos |
| `precio_compra_centavos` | Precio pactado por unidad, en centavos enteros, sin IVA |
| `lote_minimo` | Unidades mínimas que exige el distribuidor |
| `presentacion` | Descripción del empaque |
| `proveedor_id` | Proveedor (ver verificación de proveedor) |
| `banda_min_centavos`, `banda_max_centavos` | Referencia de precio para detectar sobreprecio |
| `tasa_iva_pct` | Tasa de IVA por producto (0 o 16); el valor lo valida contabilidad |
| `vigencia_hasta` | Fecha hasta la que vale la cotización |

---

## 3. Flujo
```
[ Alerta (riesgo ≥ 0.50) ] ─► [ Demanda y existencia ] ─► [ Cantidad en lotes ]
                                                                  │
[ Resumen semanal ] ◄─ [ Techo de presupuesto (opcional) ] ◄─ [ Subtotal en centavos ]
```

---

## 4. Cantidad sugerida

- $D$ = demanda media diaria de los últimos 14 días, **solo con días en que había existencia** (en un quiebre las ventas quedan limitadas por el inventario y subestiman la demanda).
- $C$ = cobertura objetivo en días (propuesta: 10, igual a la política de reposición del dataset).
- $E$ = existencia vigente; $T$ = unidades en tránsito (órdenes `aprobada` o `emitida` aún no recibidas).
- $L$ = lote mínimo.

$$\text{Necesidad} = \max(0,\; D \cdot C - E - T)$$

$$\text{Cantidad} = \max\!\left(1,\; \left\lceil \frac{\text{Necesidad}}{L} \right\rceil\right) \cdot L$$

Siempre se pide al menos un lote, porque hay una alerta. Los importes usan centavos enteros y se redondean hacia arriba solo en la cantidad, nunca en el dinero.

$$\text{Subtotal} = \text{Cantidad} \times \text{Precio (centavos)} \qquad \text{IVA} = \text{Subtotal} \times \frac{\text{tasa}}{100} \qquad \text{Total} = \text{Subtotal} + \text{IVA}$$

El presupuesto de la semana es la suma de los totales de las líneas. El IVA de cada línea se redondea al centavo.

**Ejemplo ilustrativo (cifras ficticias):** $D = 14$, $C = 10$, $E = 28$, $T = 0$, $L = 30$. Necesidad $= 140 - 28 = 112$; lotes $= \lceil 112/30 \rceil = 4$; cantidad $= 120$ unidades; a 18.50 MXN la unidad, subtotal $= 2{,}220.00$ MXN.

---

## 5. Banderas por línea
- `sin_precio`: el producto no está en el catálogo; la línea no se suma.
- `precio_vencido`: `vigencia_hasta` anterior a la fecha de corte; se pide recotizar antes de aprobar.
- `fuera_de_banda`: el precio sale de la banda por más de la tolerancia (propuesta: 10 %).

## 6. Techo semanal (opcional)
Si se define un techo, se financia en este orden: peso del cuadrante, mayor riesgo, menos cobertura. **Cada línea se financia completa o no se financia** (el lote mínimo no se divide). Lo que no cabe queda como `no_financiado` y se informa el faltante.

## 7. API
`GET /api/zenit/presupuesto?fecha_corte=2026-10-22&techo=...` devuelve líneas, total, `financiado`, `no_financiado` y `faltante`. El **Copiloto Local** consulta este mismo resultado.

## 8. Comparativo de cotizaciones
Cuando un producto tiene cotización de dos o más proveedores **verificados**, ZENIT muestra las opciones lado a lado: precio, cumplimiento histórico y tiempo de entrega.
- Productos Apalancamiento y No críticos: se sugiere el menor precio dentro de la banda.
- Productos Estratégicos y Cuello de botella: se sugiere el proveedor de mayor cumplimiento, aunque cueste más.
- La elección final la hace una persona.

## 9. Comparación con el mercado
En el prototipo se usan bandas sintéticas. En operación real, las bandas salen de cotizaciones de varios proveedores o de la fuente que el equipo defina; ZENIT no inventa precios de mercado.

## 10. Cómo se verifica
El total es la suma exacta de los totales en centavos; el ejemplo de la sección 4 da 222,000 centavos de subtotal; con una tasa de 16 % el IVA es 35,520 centavos y el total 257,520; una línea sin precio no entra al presupuesto; con techo nunca se supera el monto.
