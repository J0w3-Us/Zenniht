# Acción ZENIT: Copiloto Local de Consultas (nueva)

Responde preguntas del dueño sobre el desabasto con lenguaje natural, sin servicios externos ni costo.

---

## 1. Propósito
Dar acceso rápido a la información de ZENIT. **Solo lee**: no aprueba, no compra, no cambia nada.

## 2. Principios
- Corre local, sin LLM de pago ni internet.
- **No inventa cifras:** cada respuesta sale de una consulta a `zenith.db` y cita la tabla y la fecha de corte.
- Si no entiende la pregunta, lo dice y muestra las preguntas que sí sabe responder.

## 3. Flujo
```
[ Pregunta ] ─► [ Normalizar (minúsculas, sin acentos) ] ─► [ Detectar intención ] ─► [ Extraer producto, fecha o monto ]
                                                                                              │
[ Respuesta con fuente ] ◄─ [ Consulta SQL parametrizada, conexión de solo lectura ] ◄───────┘
```

## 4. Intenciones
| Pregunta de ejemplo | Fuente |
| --- | --- |
| ¿Qué me va a faltar esta semana? | `predicciones` (riesgo ≥ 0.50), orden Kraljic |
| ¿Cuánto cuesta surtir lo crítico? | Presupuesto de la fecha de corte |
| ¿Por qué está en rojo la insulina? | Riesgo, existencia, cobertura, ventas de 7 días, días desde el resurtido |
| ¿Qué órdenes están pendientes? | `ordenes` en estado `pendiente` |
| ¿Qué falta por recibir? | Órdenes `emitida` o `recibida_parcial` |
| ¿Qué productos estratégicos están en riesgo? | `predicciones` filtradas por cuadrante |
| ¿Cuánto no alcanza con un techo de 20,000? | Presupuesto con techo |
| ¿Qué lotes vencen pronto y cuánto dinero está en riesgo? | `lotes` y valor en riesgo |
| ¿Hubo temperaturas fuera de rango? | `lecturas_frio` |
| ¿Qué facturas faltan por conciliar? | `comprobantes` |
| ¿Cuánto llevamos gastado esta semana por cuadrante? | Comprobantes y órdenes |

## 5. Entendimiento sin costo
Reglas de palabras clave y sinónimos para la intención; para el producto, coincidencia aproximada contra los 50 nombres del catálogo con la biblioteca estándar (`difflib`); fechas y montos con expresiones regulares.

## 6. Seguridad
- Consultas siempre parametrizadas (nunca se arma SQL con el texto del usuario).
- Conexión de solo lectura (`file:zenith.db?mode=ro`).
- Si piden «aprueba la orden de…», responde que debe hacerlo en la bandeja.

## 7. Ejemplo
> **Dueño:** ¿por qué está en rojo el losartán?
> **ZENIT:** Losartán 50 mg (Estratégico) tiene riesgo semanal de <valor> al corte 2026-10-22: existencia de <n> unidades, cobertura de <n> días y ventas de 7 días de <n>. *Fuente: predicciones y ventas.*

Los valores salen de la base de datos; el ejemplo no contiene cifras reales.

## 8. Cómo se verifica
Cada intención tiene una prueba con la respuesta esperada; una pregunta fuera de lista no inventa datos; un intento de inyección SQL no devuelve ni modifica nada.
