# Sección 2: Arquitectura técnica frugal (¿cómo lo hacemos sin dinero?)

Continúa `CLAUDE.md` y la Sección 1 (`docs/02_RESTRICCIONES_SECCION_1.md`). Esta sección justifica las decisiones técnicas que mantienen el costo en **0.00 MXN** y define el pipeline del prototipo. Todo lo que se decida aquí es el mismo material que se evalúa en la Sección 3 y no cambia después.

## Qué hay que entregar
1. Casillas de estrategias técnicas, cada una con justificación técnica y económica.
2. Pipeline narrativo y secuencial: Frontend → Backend → Lógica de IA → Salida, con diagrama de bloques.
3. Declaración explícita de costo 0.00 MXN y viabilidad local en aula.

## 1. Casillas marcadas

| Casilla | Marcada | Justificación |
| --- | --- | --- |
| Free Tiers de APIs (Hugging Face, OpenAI, Gemini) | **No** | La Sección 1 exige ejecutar sin internet ni servidores externos. Una API gratuita tiene cuotas y condiciones que el proveedor puede cambiar, y la directriz de la materia prohíbe APIs comerciales. El prototipo no las necesita: el modelo se entrena y corre en local. |
| Modelos locales de código abierto (Edge/Local AI) | **Sí** | Corre el mismo algoritmo del escenario real: Temporal Fusion Transformer (`pytorch-forecasting`, `hidden_size` 16) en CPU. Es un modelo pequeño (menos de 0.05 GB, estimado), no un LLM como Phi-3 o Llama-3-8B, porque el problema es pronosticar series de tiempo y no generar texto. Se entrena antes de la clase y en el aula solo hace inferencia. Requisitos mínimos estimados, a confirmar en la laptop más modesta del equipo: CPU de 4 núcleos, 8 GB de RAM, unos 2 GB libres en disco para PyTorch en versión CPU, sin GPU. |
| Datos sintéticos y maquetas | **Sí, solo los datos** | Los 4,500 registros (50 productos × 90 días) son sintéticos y salen de `data/generar_datos.py` con semilla fija; así la farmacia es ficticia y no hay datos de pacientes. **No** se usan JSON estáticos para simular respuestas de IA. Si falta el checkpoint o falla el TFT, se muestra un error: no hay modo respaldo y no se presenta una predicción simulada como resultado. |
| Otras estrategias de costo cero | **Sí** | Python, SQLite (dominio público), PyTorch (licencia BSD), pytorch-forecasting (MIT), pytest, Git y GitHub gratuitos, y el repositorio Jarbis modificado (confirmar su licencia en `docs/JARBIS_INVENTARIO.md`). Todo es software libre, sin licencias comerciales ni servidores. |

### Costo por componente
| Componente | Licencia o costo | Costo en MXN |
| --- | --- | --- |
| Python, SQLite | Libre / dominio público | 0.00 |
| PyTorch, pytorch-forecasting | BSD / MIT | 0.00 |
| Backend e interfaz de Jarbis | A confirmar en el inventario | 0.00 |
| Datos | Sintéticos, generados por script | 0.00 |
| Entrenamiento e inferencia | CPU de la laptop del equipo | 0.00 |
| Nube, APIs, servidores | No se usan | 0.00 |

## 2. Pipeline de prototipado

### Diagrama
```
[Frontend: interfaz web de Jarbis adaptada]
   1. Cargar ventas.csv ─────────┐
   2. «Predecir desabasto» ──────┤
   3. «Aprobar orden» ───────────┤
                                 ▼
[Backend local de Jarbis]  ←→  [SQLite: ventas, predicciones, ordenes]
   /cargar    /predecir    /ordenes
                                 │
                                 ▼
[Lógica de IA: modelo/predecir.py]
   TFT local (CPU) → probabilidad diaria para 7 pasos → riesgo agregado de desabasto a 7 días
   kraljic.py      → ordena: Estratégico y Cuello de botella primero
                                 │
                                 ▼
[Salida]  tabla de 50 filas, celdas rojas si probabilidad ≥ 0.50,
          orden de compra sugerida pendiente de aprobación
```

### Narrativa paso a paso
1. **Frontend.** El usuario (el dueño de la farmacia ficticia) hace tres cosas: carga `ventas.csv`, pulsa «Predecir desabasto» y revisa la tabla; si una alerta le convence, aprueba la orden sugerida. La interfaz es la web local de Jarbis, adaptada; no necesita servicios externos. El stack concreto se confirma en `docs/JARBIS_INVENTARIO.md`.
2. **Backend y almacenamiento.** El backend local recibe el CSV, valida que tenga las 8 columnas y lo guarda en SQLite (`zenith.db`, tabla `ventas`). Las predicciones y las órdenes se guardan en las tablas `predicciones` y `ordenes` de la misma base. Todo queda en un archivo local; no hay red.
3. **Lógica de IA.** Interviene **al pulsar «Predecir desabasto»**, no al cargar los datos. `modelo/predecir.py` carga el checkpoint entrenado, toma el historial de los 50 productos y pronostica el quiebre diario para los siete días siguientes. Corrige el sesgo de la pérdida ponderada y agrega las probabilidades con `1 - producto(1 - p_diaria)`, suponiendo independencia entre días; es **modelo local real**, no mockup ni regla estática. Después `kraljic.py` ordena la lista según el cuadrante.
4. **Salida.** La tabla muestra exactamente 50 filas; las celdas con probabilidad de 0.50 o más se pintan de rojo y el sistema crea una orden sugerida en estado «pendiente». El umbral de 0.50 es el valor por defecto; si el equipo lo cambia, debe actualizarse también en la Sección 3 antes de la presentación.
5. **Aprendizaje.** `modelo/evaluar.py` compara las predicciones con la existencia real de los últimos 27 días y calcula el F1-Score; el reentrenamiento se hace a mano con `entrenar_tft.py`.

### Por qué escala
El escenario real usa la misma cadena: ventas → TFT → ponderación Kraljic → orden sugerida con aprobación humana → comparación con la realidad. Para pasar de 1 a 15,000 sucursales se replica la instalación local y se cambia SQLite por una base de datos en la nube; el algoritmo y la lógica de negocio no cambian.

## 3. Declaración de cumplimiento (texto para el reporte)
«El prototipo de ZENIT tiene un costo financiero de **0.00 MXN**: usa únicamente software libre (Python, SQLite, PyTorch y pytorch-forecasting), datos sintéticos y la CPU de las computadoras del equipo, sin APIs de pago, nube ni licencias comerciales. Corre de forma local en una computadora personal común, sin internet ni configuración de red. Mantiene el mismo algoritmo y la misma lógica de negocio del escenario real (Sección 1) y usa el mismo dataset cerrado de 50 productos y 90 días que se evaluará en los Hitos de Validación (Sección 3).»

## Reglas para la IA que construye esto
- No agregues APIs externas, ni siquiera gratuitas, ni descargas de modelos preentrenados.
- No sustituyas el TFT por reglas, JSON estáticos, valores por defecto ni otro modelo; si falla, informa el error.
- No cambies el dataset, el umbral de 0.50 ni las columnas sin avisar: afectan a la Sección 3.
- No ejecutes compras, pagos ni contactos con proveedores; las órdenes sugeridas requieren aprobación humana explícita.
- Si algo de Jarbis depende de internet o de pago, apártalo y avísalo.

## Cómo se evalúa esta sección (rúbrica del maestro)
- Estrategia de escala y frugalidad (40%): reducción lógica y costo explícito de cero pesos.
- Arquitectura del pipeline (30%): cómo interactúan Frontend y Backend y cómo se ejecuta la IA a escala.
