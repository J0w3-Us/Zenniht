# Acción ZENIT: Verificación de Proveedores (nueva)

Antes de enviar un pedido, la persona comprueba que el proveedor existe y está en regla. ZENIT guarda el resultado y avisa si falta.

---

## 1. Propósito
Reducir el riesgo de comprar a un proveedor no confiable y medir su desempeño, que alimenta el criterio de «riesgo de suministro» de Kraljic.

## 2. Flujo
```
[ Proveedor nuevo o vencido ] ─► [ Verificación manual ] ─► [ Registro en proveedores ]
                                                                      │
              [ Advertencia en la aprobación; bloqueo de «emitida» ] ◄┘ (si no está verificado)
```

## 3. Qué se verifica (lo hace una persona)
Razón social, RFC con formato válido (12 caracteres en persona moral, 13 en persona física), estatus fiscal y el documento sanitario que corresponda a un distribuidor de medicamentos, según el responsable sanitario de la farmacia.

## 4. Fuentes
La fuente la elige el equipo (decisión D5): consulta pública del SAT, OpenCorporates u otra. No verifiqué la cobertura de OpenCorporates para proveedores mexicanos.
- **Con red:** se consulta la fuente elegida y se guardan el enlace (`fuente_url`), la fecha de la consulta y el resultado.
- **Sin red (demostración en aula):** se usan proveedores ficticios ya verificados o una verificación manual.

## 5. Registro (`proveedores`)
Razón social, RFC (ficticio en el prototipo), estatus (`pendiente`, `verificado`, `rechazado`, `vencido`), fuente, fecha y vigencia (propuesta: 12 meses).

## 6. Reglas
- Una orden a un proveedor no verificado se puede aprobar con advertencia roja, pero no se puede marcar `emitida`.
- Al vencer la vigencia, el estatus pasa a `vencido`.

## 7. Desempeño
Con los datos de recepción: cumplimiento (cantidad recibida ÷ pedida), tiempo de entrega y rechazos por cadena de frío o caducidad. Un cumplimiento bajo sugiere revisar el cuadrante del producto.

## 8. Cómo se verifica
Un proveedor `vencido` bloquea `emitida`; un RFC con longitud inválida se rechaza; el cumplimiento de una recepción parcial se calcula bien.
