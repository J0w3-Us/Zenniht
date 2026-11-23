# Acción ZENIT: Caducidad, Rotación FEFO y Merma (nueva)

Evita perder producto por vencimiento y evita que una compra deje inventario que no se alcanzará a vender.

---

## 1. Propósito
Vigilar la caducidad de cada lote, indicar qué vender primero y estimar cuánto dinero está en riesgo. Complementa al pronóstico de desabasto: pedir de más también es un problema.

## 2. Flujo
```
[ Lotes con caducidad ] ─► [ Días restantes y demanda ] ─► [ Unidades en riesgo ] ─► [ Valor en riesgo ]
                                                                    │
                    [ Acción propuesta, decidida por una persona ] ◄┘
```

## 3. Datos
Tabla `lotes`: lote, producto, caducidad, cantidad inicial, cantidad actual y estado. Con el dataset canónico hay un lote por producto, creado al cargar. Cada recepción aceptada crea uno nuevo.

**Nota para la demostración:** en el dataset sintético ningún lote vence en menos de 180 días. Para mostrar esta acción se usa un lote de prueba con caducidad corta, cargado como dato aparte; no se modifica `ventas`.

## 4. Estados de un lote
| Estado | Condición |
| --- | --- |
| `vigente` | Más días restantes que el umbral de aviso |
| `proximo` | Días restantes ≤ umbral de aviso (propuesta: 90) |
| `en_riesgo` | Unidades en riesgo mayor a 0 |
| `vencido` | Días restantes ≤ 0; no se puede vender |
| `bloqueado` | Retiro de lote o revisión de frío; no suma a la existencia vigente |

## 5. Cálculo
Con $D$ la demanda diaria media (solo días con existencia), $E$ las unidades del lote y $R$ los días restantes hasta la caducidad:

$$\text{Unidades en riesgo} = \max(0,\; E - D \cdot R)$$

$$\text{Valor en riesgo} = \text{Unidades en riesgo} \times \text{Precio de compra (centavos)}$$

## 6. FEFO
Si hay más de un lote del mismo producto, la interfaz indica **vender primero el que caduca antes**.

## 7. Acciones propuestas (las decide una persona)
Vender primero ese lote, ofrecer una promoción, pedir devolución al proveedor si el acuerdo lo permite, o registrar la **merma** con su motivo (caducidad, daño, temperatura) en `movimientos_inventario`. ZENIT nunca da de baja inventario por su cuenta.

## 8. Relación con las órdenes
Si una orden `pendiente` dejaría unidades en riesgo de vencer, la pantalla de aprobación muestra una advertencia con el valor en riesgo. No bloquea la aprobación.

## 9. Cómo se verifica
Un lote con 10 días restantes y existencia mayor a $D \cdot 10$ calcula bien las unidades en riesgo; un lote vencido no suma a la existencia vigente; registrar merma crea un movimiento y deja una fila en `bitacora`.
