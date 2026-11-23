# ZENIT: análisis de las acciones y convenciones comunes (versión 2)

Revisé los archivos de acciones contra lo ya comprometido (Secciones 1 a 3 de la Actividad 3 y `CLAUDE.md`). En esta versión ZENIT ya no se trata como un sistema solo de desabasto: el pronóstico es un módulo más, junto con compras, presupuesto, proveedores, recepción, caducidad, cadena de frío y contabilidad básica.

> **Supuesto que debes confirmar:** no me dijiste qué áreas nuevas cubre ZENIT. Amplié el alcance con las que ya aparecían en tus archivos originales (compras, proveedores, comprobantes) y en el escenario real de la Sección 1 (caducidades, cadena de frío, lotes). Si hay otras, se agregan como una acción más.

## 1. Alcance de ZENIT en estos archivos
| Área | Acciones |
| --- | --- |
| Datos | carga de datos |
| Abasto | pronóstico TFT, priorización de Kraljic, evaluación del modelo |
| Compras y finanzas | presupuesto y cotización, precios unitarios, aprobación de órdenes, verificación de proveedor, comprobantes y contabilidad |
| Operación de inventario | recepción de mercancía, caducidad y merma, cadena de frío |
| Apoyo | Copiloto Local, verificación de hitos |

## 2. Hallazgos y correcciones

| # | Archivo | Hallazgo | Gravedad | Corrección |
| --- | --- | --- | --- | --- |
| 1 | prediccion_tft | El riesgo semanal 1 − ∏(1 − p) supone eventos diarios independientes. Un quiebre persiste hasta el resurtido, así que con probabilidades marginales el riesgo se sobrestima. | Crítica | `p_diaria` se define como riesgo instantáneo (primer quiebre en el día t, dado que no hubo antes); con esa definición la fórmula es exacta. Si no se entrena así, se usa el evento semanal directo. |
| 2 | priorizacion_kraljic | El diagrama intercambia Apalancamiento y Cuello de botella respecto a la definición. | Crítica | Diagrama corregido. |
| 3 | aprobacion_ordenes, precios_unitarios | «Emisión formal de la orden» y «Compra» aparecen como pasos del sistema, lo que contradice la regla de no actuar solo y las exclusiones 2 y 5 de la Sección 2. | Crítica | ZENIT genera la hoja de orden; una persona la envía y lo registra. |
| 4 | precios_unitarios | OpenCorporates es un registro de empresas, no almacena comprobantes. No verifiqué su cobertura de proveedores mexicanos. | Media | Se **restableció** como validación del proveedor cuando hay red; los comprobantes se guardan en disco local y hacen referencia al registro validado. |
| 5 | presupuesto_cotizacion, precios_unitarios | `catalogo_precios.json` agrega datos fuera del dataset cerrado de la Sección 1. | Alta | Tabla complementaria y sintética, separada de `ventas`, que no toca la huella SHA-256 ni los hitos. |
| 6 | prediccion_tft | La temperatura entraría como variable conocida del futuro, pero no lo es. | Alta | Solo como dato observado del pasado; futuro conocido: día de la semana y quincena. |
| 7 | prediccion_tft, Sección 1 | La Sección 1 lista el cuadrante como entrada del modelo, pero la regla de integridad dice que Kraljic nunca altera la probabilidad. | Alta | Decisión pendiente (D2); recomendado: el cuadrante queda fuera del modelo. |
| 8 | carga_datos, recepción | Registrar una recepción cambiaría `existencia`, pero `ventas` es canónica e inmutable. | Alta | Tabla `movimientos_inventario`, tabla `lotes` y vista de existencia vigente. |
| 9 | presupuesto_cotizacion | Cantidad sugerida ambigua; las ventas durante un quiebre subestiman la demanda; dinero con decimales. | Media | Fórmula con lote, tránsito y cobertura; demanda solo de días con stock; importes en centavos enteros. |
| 10 | aprobacion_ordenes | Faltan estados, usuario, motivo y protección contra doble aprobación; `CURRENT_TIMESTAMP` es UTC sin zona. | Media | Máquina de estados, bitácora, código 409 y UTC en ISO 8601. El cierre contable se **restableció** y ahora tiene su propia acción. |
| 11 | carga_datos | Sin manejo de errores, atomicidad ni idempotencia. | Media | Validaciones en orden, transacción única y dos modos. |
| 12 | presupuesto_cotizacion | Menciona un «Copiloto Local» no definido. | Media | Acción nueva. |
| 13 | prediccion_tft | Con unos 1.6 % de ventanas positivas en entrenamiento, el umbral de 0.50 puede casi no alcanzarse. | Media | Se mide calibración y se reporta; el umbral no se cambia. |
| 14 | priorizacion_kraljic | Sin criterios de clasificación ni orden dentro del cuadrante. | Media | Puntajes de impacto y riesgo, y clave de orden. |
| 15 | presupuesto_cotizacion | No consideraba IVA ni comparación de cotizaciones. | Media | **Restablecido:** IVA por producto (la tasa la valida contabilidad) y comparativo de proveedores. |
| 16 | precios_unitarios | Nombre de archivo con espacio. | Baja | `precios_unitarios.md`. |

## 3. Decisiones que necesita el equipo
- **D1. Cómo se entrena el riesgo:** riesgo instantáneo diario (se mantiene la fórmula del producto) o evento semanal directo.
- **D2. Cuadrante de Kraljic:** dentro o fuera del modelo; si queda fuera, hay que ajustar la frase de la Sección 1.
- **D3. Cobertura objetivo:** propuse 10 días, igual a la política de reposición del dataset.
- **D4. Rigor del Hito de Salida:** pide celdas rojas solo en productos que de verdad quedan en cero (precisión de 100 % el 2026-10-22). Un solo falso positivo lo reprueba; conviene ensayarlo.
- **D5. Fuente de verificación de proveedores:** OpenCorporates, consulta pública del SAT o registro propio.
- **D6. Áreas nuevas de ZENIT:** confirmar si faltan más allá de las de la sección 1.

## 4. Convenciones comunes

### Estados de una orden
```
pendiente ──► aprobada ──► emitida ──► recibida ──► cerrada
    │             │                        └─► recibida_parcial ─► cerrada
    ├──► descartada (con motivo)
    ├──► pospuesta (con fecha) ──► pendiente
    └──► obsoleta (el riesgo ya no justifica la orden)
```
Solo una persona mueve `pendiente → aprobada`, `aprobada → emitida` y `pendiente → descartada o pospuesta`. El sistema solo crea órdenes `pendiente` y marca `obsoleta`.

### Tablas (`zenith.db`)
| Tabla | Contenido |
| --- | --- |
| `ventas` | Dataset canónico, 4,500 filas. Inmutable tras la carga. |
| `lotes` | Lote, producto, caducidad, cantidad inicial y actual, estado. |
| `movimientos_inventario` | Entradas por recepción, mermas y ajustes. |
| `catalogo_precios` | Complementaria y sintética: precio en centavos, lote mínimo, presentación, proveedor, banda de precio, tasa de IVA, vigencia. |
| `proveedores` | Razón social, estatus de verificación, fuente y enlace, fecha, vigencia, plazo de pago. |
| `predicciones` | Fecha de corte, producto, riesgo semanal, riesgos diarios, versión del modelo, milisegundos. |
| `ordenes` | Estado, cantidad, importes en centavos, quién y cuándo decidió, motivo, versión. |
| `recepciones` | Cantidad, caducidad, temperatura, ruta y SHA-256 del comprobante. |
| `comprobantes` | Tipo, folio, proveedor, importes, archivo y SHA-256, estado de conciliación, pago. |
| `lecturas_frio` | Equipo, fecha y hora, temperatura, quién la registró. |
| `evaluaciones` | Matriz de confusión, precisión, recall, F1 y número de positivos. |
| `bitacora` | Evento, entidad, usuario, detalle y fecha UTC. |

### Parámetros
| Congelados (Secciones 1 a 3) | Ajustables (con aviso al equipo) |
| --- | --- |
| 4,500 filas, 50 productos, 90 días; huella SHA-256 del CSV; horizonte de 7 días; umbral 0.50; `hidden_size` 16; CPU; límite de 1,000 ms; fecha de demostración 2026-10-22 | Ventana del encoder (28 días); cobertura objetivo (10 días); techo semanal; tolerancia de precio (10 %); caducidad mínima al recibir y aviso de caducidad (90 días); vigencia de verificación de proveedor (12 meses); intervalo de lecturas de frío (4 horas) |

Los ajustables son propuestas mías, no datos del proyecto. El rango de 2 a 8 °C es el habitual para insulinas y vacunas.

### Rutas de la API
`POST /api/zenit/datos/cargar` · `POST /api/zenit/predicciones` · `GET /api/zenit/alertas` · `GET /api/zenit/presupuesto` · `GET /api/zenit/ordenes` · `POST /api/zenit/ordenes/{id}/aprobar | descartar | posponer | emitir` · `POST /api/zenit/recepciones` · `GET /api/zenit/lotes` · `POST /api/zenit/frio/lecturas` · `POST /api/zenit/comprobantes` · `GET /api/zenit/evaluacion` · `POST /api/zenit/copiloto` · `GET /api/zenit/verificacion/hitos`

### Reglas generales
- Fechas y horas en UTC con formato ISO 8601; la interfaz las muestra en la zona horaria configurada.
- Importes en centavos enteros; solo se formatean a MXN al mostrarlos.
- Consultas SQL siempre parametrizadas.
- Todo cambio de estado deja una fila en `bitacora`.
- ZENIT nunca compra, paga, timbra ni da de baja inventario por su cuenta: lo hace una persona.
- Costo 0.00 MXN: ninguna acción requiere APIs de pago ni nube; lo que usa internet es opcional y fuera de la demostración.

## 5. Mapa de archivos
| Archivo | Estado |
| --- | --- |
| accion_zenit_carga_datos | Mejorada |
| accion_zenit_prediccion_tft | Mejorada |
| accion_zenit_priorizacion_kraljic | Mejorada |
| accion_zenit_presupuesto_cotizacion | Mejorada |
| accion_zenit_aprobacion_ordenes | Mejorada |
| precios_unitarios | Mejorada |
| accion_zenit_recepcion_mercancia | Nueva |
| accion_zenit_evaluacion_aprendizaje | Nueva |
| accion_zenit_copiloto_local | Nueva |
| accion_zenit_verificacion_proveedor | Nueva |
| accion_zenit_verificacion_hitos | Nueva |
| accion_zenit_caducidad_merma | Nueva (alcance ampliado) |
| accion_zenit_cadena_frio | Nueva (alcance ampliado) |
| accion_zenit_comprobantes_contabilidad | Nueva (alcance ampliado) |
