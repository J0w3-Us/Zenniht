# Contexto de ZENIT

## Problema
Las farmacias de barrio piden a ojo. Cuando falta un medicamento, el paciente se va y, si es un tratamiento crónico (insulina, antihipertensivos), se interrumpe su tratamiento. Cuando sobra, el producto caduca y se tira.

## Solución
ZENIT lee las ventas, el inventario, el clima y el calendario de la farmacia, estima la probabilidad de desabasto de cada producto a 7 días, ordena las alertas con la matriz de Kraljic y sugiere órdenes de compra. El dueño aprueba; el sistema no compra ni paga solo. Cada predicción se compara después con lo ocurrido para mejorar.

## Matriz de Kraljic (impacto en el negocio contra riesgo de suministro)
| Cuadrante | Qué incluye | Estrategia |
| --- | --- | --- |
| Estratégico (alto/alto) | Patente y crónicos: insulina, antihipertensivos | Alianzas a largo plazo y predicción exacta |
| Apalancamiento (alto/bajo) | Genéricos de alta rotación: paracetamol | Compras por volumen y negociación de precio |
| Cuello de botella (bajo/alto) | Insumos de temporada: vacuna de influenza | Asegurar stock con antelación y monitoreo constante |
| No crítico (bajo/bajo) | Gasas, alcohol | Compras automatizadas y stock mínimo |

En el prototipo, las alertas de Estratégico y Cuello de botella se muestran primero.

## Arquitectura (Modelo de Torres)
Percepción (ventas, inventario, clima) → Memoria (historial en SQLite) → Razonamiento (TFT: probabilidad de desabasto) → Acción (alertas y órdenes sugeridas) → Aprendizaje (compara predicción contra realidad).

## Escenario real frente a prototipo
| Dimensión | Real (hipotético) | Prototipo |
| --- | --- | --- |
| Sucursales | 15,000 | 1 ficticia |
| Productos | 10,000 activos por sucursal | 50 |
| Registros | 6,570 millones de líneas al año | 4,500 (50 × 90) |
| Almacenamiento | Data lake en la nube | SQLite local |
| Cadena de frío | Sensores IoT | Columna `requiere_refrigeracion` |
| Recetas | NLP | Fuera del prototipo |
| Algoritmo | TFT por producto y sucursal | El mismo TFT, `hidden_size` 16, CPU |
| Costo | Nube y licencias | 0.00 MXN |
