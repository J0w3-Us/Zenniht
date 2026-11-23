# Flujo de Cotización, Validación y Aprovisionamiento Basado en Precios Unitarios

Ciclo operativo de adquisición y gestión presupuestaria de ZENIT a partir del precio unitario. Los precios del prototipo son **sintéticos** (ver presupuesto y cotización). Todo paso que implique actuar fuera del sistema lo hace una persona.

---

## Proceso 1: Ciclo de compra, cotización y registro de comprobantes

```
[ Precio unitario ] ─► [ Cantidad y subtotal ] ─► [ Banda de precio ] ─► [ Proveedor verificado ]
                                                                                   │
[ Comprobante local ] ◄─ [ Recepción ] ◄─ [ Orden enviada por una persona ] ◄─ [ Carro + aprobación ]
```

1. **Precio unitario:** se toma de `catalogo_precios` (centavos enteros, sin IVA) para cada producto en alerta. Si falta, la línea queda `sin_precio`.
2. **Cantidad y subtotal:** se calculan en lotes con la fórmula de la acción de presupuesto. Si `vigencia_hasta` ya pasó, la línea queda `precio_vencido` y se pide recotizar.
3. **Banda de precio:** se compara con `banda_min` y `banda_max` del catálogo; si sale más allá de la tolerancia (propuesta: 10 %), la línea queda `fuera_de_banda`. En el prototipo las bandas son datos sintéticos, no precios reales del mercado.
4. **Validación del proveedor:** se consulta el estatus en `proveedores` y, con red, se verifica su razón social, estatus y legitimidad en registros públicos (OpenCorporates u otra fuente, ver verificación de proveedor). Sin red se usa la verificación manual. El resultado, la fuente y su enlace se guardan localmente. OpenCorporates es un registro de empresas: sirve para validar al proveedor, no para almacenar comprobantes.
5. **Carro de compra:** se agrupan las líneas por proveedor, con cantidades, precios e inversión total en MXN.
6. **Aprobación humana:** el responsable revisa y aprueba o descarta **cada orden** (ver aprobación de órdenes).
7. **Envío:** ZENIT genera la hoja de orden; **una persona** la envía al proveedor y la marca `emitida`. El sistema no emite ni contacta a nadie.
8. **Recepción y comprobante:** inspección física (caducidad y cadena de frío), registro de la entrada y guardado del comprobante en disco local con su SHA-256. El comprobante hace referencia al registro corporativo validado del proveedor (su enlace guardado en `proveedores`) y entra a la conciliación (ver recepción de mercancía y comprobantes y contabilidad).

---

## Proceso 2: Simulación y optimización presupuestaria por cuadrante

1. **Alertas:** productos con riesgo semanal ≥ 0.50.
2. **Prioridad por Kraljic:**
   - Estratégicos y Cuello de botella: compra inmediata, aunque el costo unitario sea mayor.
   - Apalancamiento: se agrupan por proveedor para negociar volumen (Proceso 3).
   - No críticos: pedidos consolidados para reducir costo de envío y trabajo administrativo.
3. **Techo semanal:** si hay un límite de dinero, se asigna en este orden estricto:
   $$\text{Estratégico} \succ \text{Cuello de botella} \succ \text{Apalancamiento} \succ \text{No crítico}$$
   Dentro de cada cuadrante, mayor riesgo primero; cada línea se financia completa o no se financia.
4. **Informe de faltante:** lo que no cabe queda `no_financiado`, con el monto que faltaría.
5. **Cierre:** al registrar la entrada de mercancía, la existencia vigente sube y el riesgo baja en la siguiente inferencia.

---

## Proceso 3 (nuevo): Consolidación por proveedor y descuento por volumen

1. Se suman los subtotales de las líneas de **Apalancamiento** de cada proveedor.
2. Si el proveedor tiene un umbral de volumen y un porcentaje de descuento (`descuento_volumen_pct`, datos sintéticos opcionales) y la suma lo alcanza, se muestra el ahorro estimado:
   $$\text{Ahorro} = \text{Suma Apalancamiento} \times \text{descuento}$$
3. El descuento **no se aplica** al presupuesto hasta que una persona confirme la cotización con el proveedor.
4. Este proceso solo informa; no cambia cantidades ni riesgos.

---

## Proceso 4 (nuevo): Conciliación a tres vías
1. Se comparan la **orden aprobada**, la **recepción** y el **comprobante** (factura o remisión).
2. Se revisan cantidades (pedida, recibida, facturada) y precio (pactado y facturado).
3. Resultado: `conciliado` o `con_diferencia`, con el detalle de qué difiere.
4. Una persona resuelve las diferencias (nota de crédito, devolución o aceptación) y registra la decisión.

---

## Cómo se verifica
Una línea sin precio no suma; una cotización vencida bloquea la aprobación; con techo el total financiado nunca lo supera; no existe ninguna ruta del sistema que envíe un pedido.
