# Restricciones del chat de Zenit

Implementadas el 23 de noviembre de 2026 en `OpenJarvis/politica_agente.py`,
`agente_zenit.py` y la API del chat. Aplican a cualquier modelo local elegido.

## Alcance público

El agente atiende inventario, existencias, historial de ventas, riesgo de
desabasto, sugerencias de reabasto y cotizaciones de la farmacia. Saludos,
identidad y ayuda tienen respuestas controladas. No proporciona código,
SQL, scripts, instrucciones internas, asesoramiento clínico ni respuestas
generales de temas ajenos.

Las restricciones limitan el dominio, no reducen todas las respuestas a
desabasto. Las consultas explícitas de historial y ordenación se resuelven con
herramientas locales tipadas, incluso si Ollama no está disponible:

- «Dame los 5 productos que tenemos en mayor cantidad»: orden descendente de
  existencias al último corte, sin filtrar alertas ni mostrar tarjetas de riesgo.
- «Productos con menos existencias»: orden ascendente.
- «Los 3 productos más vendidos en los últimos 7 días»: suma ventas del periodo,
  no ordena por existencias.
- «Historial de Insulina glargina de los últimos 7 días»: ventas y existencias
  diarias en orden cronológico.
- «Historial general»: totales diarios de la farmacia; sin producto ficticio.
- «Todo el historial de Paracetamol»: hasta los 90 días disponibles.
- Se admiten fechas ISO explícitas para el historial; nombres ambiguos como
  «Insulina» requieren elegir el producto en lugar de tomar el primero.

El resumen general presenta unidades y mayores existencias. Las alertas
detalladas y sus tarjetas se muestran cuando se piden riesgos o predicción;
no se añaden automáticamente a una consulta de cantidades o historial.

## Controles implementados

1. La entrada se normaliza y rechaza solicitudes técnicas, cambios de rol,
   revelación de instrucciones y solicitudes clínicas reconocibles. Una
   consulta sin relación con el catálogo o las operaciones se rechaza. Los
   seguimientos breves necesitan contexto operativo permitido.
2. Solo se aceptan las siete herramientas de consulta operativa y predicción.
   El chat no anuncia ni ejecuta SQL libre, comandos del sistema, aprobaciones,
   compras ni pagos. Los argumentos se comprueban contra el contrato de cada
   herramienta; hay un máximo de cuatro ejecuciones por turno.
3. El historial enviado por el navegador no puede introducir mensajes de
   sistema ni respuestas de asistente utilizadas como instrucciones.
4. **Nunca se entrega el texto libre generado por Ollama.** El modelo selecciona
   herramientas y el servidor redacta la respuesta a partir de campos
   conocidos: productos del catálogo verificado, fechas y valores numéricos.
   Las salidas de herramientas no publican campos de texto arbitrarios.
5. Errores técnicos y trazas no se devuelven en el chat ni en su estado público.
   El diagnóstico permanece en el registro del servidor.

El filtro de palabras no se considera una defensa suficiente por sí solo.
Aunque una variante de solicitud atraviese ese filtro, el texto del modelo
no se publica. A cambio, el chat deja de ofrecer narraciones libres y respuestas
creativas: presenta formatos operativos controlados. Las consultas analíticas
que requieran nuevas operaciones deben implementarse como herramientas
tipadas con su propio formato de salida, en lugar de reabrir SQL libre.

Las predicciones, probabilidades y cantidades siguen calculándose en los
motores existentes; esta política no las simula ni modifica. Las aprobaciones
continúan siendo acciones manuales en la interfaz.

## Verificación

`tests/zenit/test_politica_agente.py` prueba solicitudes de código en español
e inglés, caracteres invisibles, temas generales, consultas clínicas,
extracción del prompt, historial falsificado, texto malicioso generado por
el modelo, herramientas y argumentos no permitidos, errores internos y
cotizaciones válidas. La suite completa de ZENIT pasa 65 pruebas.

La frontera protege el chat servido por la API de Zenit. No cambia las
capacidades del modelo base cuando se usa directamente desde otra aplicación
o desde la consola de Ollama. Tampoco elimina mensajes antiguos ya guardados
en el navegador; esos mensajes no se reenvían como instrucciones del asistente.
