# Acción ZENIT: Comprobantes, Conciliación y Contabilidad Básica (nueva)

Registra lo que se compró, lo que llegó y lo que se facturó, y prepara la información para el contador.

---

## 1. Propósito
Cerrar el ciclo financiero de cada orden: que lo pedido, lo recibido y lo facturado coincidan, y llevar el IVA y lo que se debe a cada proveedor. **ZENIT no paga ni timbra facturas**; solo registra y concilia.

## 2. Flujo
```
[ Orden aprobada ] ─┐
[ Recepción ]       ├─► [ Conciliación a tres vías ] ─► [ conciliado / con_diferencia ] ─► [ Cuentas por pagar ]
[ Comprobante ]    ─┘                                                                         │
                                                              [ Informe para el contador (CSV) ] ◄┘
```

## 3. Comprobantes (`comprobantes`)
Tipo (factura o remisión), folio, proveedor, fecha, subtotal, IVA y total en centavos, archivo guardado en disco local con su SHA-256, y estado (`registrado`, `conciliado`, `con_diferencia`, `pagado_por_persona`).
- Las facturas electrónicas mexicanas son CFDI. El prototipo guarda el archivo y captura el folio fiscal (UUID); **no** valida el CFDI ante el SAT (eso requiere red y queda como opción).
- El par proveedor y folio es único: un comprobante no se puede registrar dos veces.

## 4. Conciliación a tres vías
Se comparan, por producto:
- **Cantidad:** pedida, recibida y facturada.
- **Precio:** pactado y facturado.
- **IVA y totales:** el IVA se recalcula por línea y el total debe ser subtotal más IVA.

Cualquier diferencia en centavos deja el comprobante `con_diferencia` y se muestra qué línea falla. Una persona decide: nota de crédito, devolución o aceptación.

## 5. Cuentas por pagar
El vencimiento es la fecha del comprobante más el plazo del proveedor (`plazo_pago_dias`, dato sintético). Una **persona** marca «pagado» con fecha y referencia; ZENIT no ejecuta pagos.

## 6. Informes
- Gasto por semana, por proveedor y por cuadrante de Kraljic.
- Comprobantes con diferencia y pagos por vencer.
- Exportación a CSV para el contador.

## 7. Cómo se verifica
Un comprobante con total distinto de subtotal más IVA se marca con diferencia; registrar dos veces el mismo folio del mismo proveedor se rechaza; una recepción parcial facturada completa queda `con_diferencia`; el archivo guardado conserva su SHA-256.
