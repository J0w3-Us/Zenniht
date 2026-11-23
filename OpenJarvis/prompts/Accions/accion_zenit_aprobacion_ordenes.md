# Acción ZENIT: Aprobación Humana de Órdenes (Human-in-the-Loop)

Gobierno y seguridad operativa de ZENIT: toda decisión de compra la toma una persona.

---

## 1. Regla inquebrantable

> **ZENIT nunca compra, paga, emite pedidos ni contacta a proveedores por su cuenta.** Toda orden sugerida queda `pendiente` hasta que una persona la autoriza, una por una, en la interfaz. ZENIT solo prepara la hoja de la orden; **quien la envía al proveedor es una persona**.

Esto cumple las exclusiones 2 y 5 de la Sección 2.

---

## 2. Estados y quién los cambia

```
pendiente ─► aprobada ─► emitida ─► recibida ─► cerrada
   ├─► descartada (motivo obligatorio)
   ├─► pospuesta (hasta una fecha) ─► vuelve a pendiente
   └─► obsoleta (la pone el sistema cuando el riesgo ya no la justifica)
```

| Transición | Quién |
| --- | --- |
| Crear `pendiente`, marcar `obsoleta` | Sistema |
| `aprobada`, `emitida`, `descartada`, `pospuesta` | Persona identificada |
| `recibida`, `cerrada` | Persona (ver recepción) |

---

## 3. Revisión antes de aprobar
La pantalla muestra producto, cuadrante, riesgo, existencia vigente, caducidad del lote, cantidad, precio, subtotal y banderas de precio. Opcionalmente el operador captura la **existencia física contada**; si difiere de la del sistema, aparece una advertencia.

- Hay un cuadro de confirmación con el subtotal en MXN.
- **No existe aprobación masiva.**
- Si el proveedor no está verificado, aparece una advertencia roja y no se podrá marcar como `emitida`.

## 4. Descartar o posponer
Requieren un **motivo** de la lista: ya surtido, error de predicción, sin presupuesto, proveedor no disponible u otro. Posponer guarda una fecha de regreso. Los motivos «error de predicción» se cuentan para la evaluación del modelo (no reentrenan nada por sí solos).

## 5. Persistencia
- Se guarda `estado`, `decidida_por`, `decidida_en` en UTC con formato ISO 8601 (no `CURRENT_TIMESTAMP` sin zona) y el `motivo`.
- Control de versión de la fila: aprobar dos veces la misma orden devuelve **409** y no cambia nada.
- Cada cambio escribe en `bitacora`.
- Una orden aprobada ya no se edita; si hay un error se descarta y se crea otra.

## 6. Emisión y cierre contable
Al aprobar, ZENIT genera la **hoja de orden** (CSV o página imprimible). La persona la envía y pulsa «Marcar como enviada»; ese acto pasa la orden a `emitida`. La orden queda en la bitácora para surtimiento y entra a la cola de **comprobantes y conciliación** (ver acción de comprobantes y contabilidad).

## 7. API
`POST /api/zenit/ordenes/{id}/aprobar | descartar | posponer | emitir` (cuerpo con `usuario` y, según el caso, `motivo`, `hasta` o `existencia_fisica`). Códigos: 200, 404, 409 (estado inválido) y 422 (faltan datos).

## 8. Cómo se verifica
Sin usuario no se puede aprobar; una segunda aprobación devuelve 409; la búsqueda en el código muestra un solo lugar que escribe `aprobada` y es el endpoint de aprobación; descartar sin motivo devuelve 422.
