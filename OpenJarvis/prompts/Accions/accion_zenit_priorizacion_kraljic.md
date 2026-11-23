# Acción ZENIT: Priorización Estratégica con Matriz de Kraljic

Ordena las alertas de desabasto según su relevancia clínica y la dificultad de conseguir el producto.

---

## 1. Propósito

Decidir **qué se atiende primero** entre las alertas que ya produjo el modelo.

> **Regla de integridad:** Kraljic ordena la presentación y la asignación de presupuesto. **Nunca** cambia el riesgo calculado por el TFT, no crea ni elimina alertas y no modifica el umbral de 0.50.

---

## 2. Los cuatro cuadrantes (impacto en el negocio × riesgo de suministro)

```
                     Riesgo de suministro bajo          Riesgo de suministro alto
                 ┌────────────────────────────────┬────────────────────────────────┐
  Impacto alto   │ APALANCAMIENTO (15 productos)  │ ESTRATÉGICO (10 productos)     │
                 │ Paracetamol, Amoxicilina       │ Insulina glargina, Losartán,   │
                 │                                │ Metformina                     │
                 ├────────────────────────────────┼────────────────────────────────┤
  Impacto bajo   │ NO CRÍTICO (15 productos)      │ CUELLO DE BOTELLA (10)         │
                 │ Alcohol, Gasas, Curitas        │ Vacuna influenza, Oseltamivir  │
                 └────────────────────────────────┴────────────────────────────────┘
```

| Cuadrante | Estrategia | Peso de orden |
| --- | --- | --- |
| Estratégico | Alianzas con distribuidores y predicción exacta; compra inmediata | 1 |
| Cuello de botella | Asegurar stock con antelación y monitoreo constante | 2 |
| Apalancamiento | Compras por volumen y negociación de precio | 3 |
| No crítico | Compras automatizadas y stock mínimo | 4 |

---

## 3. Cómo se decide el cuadrante

En el prototipo el cuadrante es una columna fija de los datos. Para justificarlo se usan dos puntajes de 1 a 5, con corte en 3 («alto» desde 3):

- **Impacto:** criticidad clínica, continuidad del tratamiento y peso en las ventas.
- **Riesgo de suministro:** número de proveedores alternos, cadena de frío (`requiere_refrigeracion`), estacionalidad e historial de quiebres.

---

## 4. Orden de la bandeja

Clave de orden (ascendente): `(peso del cuadrante, −riesgo semanal, días de cobertura, nombre del producto)`.

1. Cuadrante: Estratégico, Cuello de botella, Apalancamiento, No crítico.
2. Dentro de cada cuadrante: mayor riesgo primero.
3. Empate: menos días de cobertura primero.
4. Último desempate: orden alfabético, para que el resultado sea siempre el mismo.

## 5. Vigilancia (opcional, no es alerta)
Lista informativa en ámbar de productos Estratégicos con riesgo entre 0.30 y 0.50. Esos valores son una propuesta; no genera órdenes ni cambia las celdas rojas del Hito de Salida.

## 6. Dónde se usa el orden
- Bandeja de alertas de desabasto.
- Asignación del techo de presupuesto (ver presupuesto y cotización).
- Atención de excursiones de temperatura: los productos Estratégicos refrigerados (por ejemplo, las insulinas) se revisan primero.
- Cola de caducidades: a igual valor en riesgo, se atiende antes el producto de mayor peso.

## 7. Cómo se verifica
Prueba automática: los riesgos son idénticos antes y después de ordenar; un producto con riesgo menor a 0.50 nunca aparece como alerta aunque sea Estratégico; el orden es el mismo en dos corridas.
