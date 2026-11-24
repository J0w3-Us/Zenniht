# Sugerencias del chat y revisión de cambios descargados

## Corrección aplicada

| Before | After | Why |
| --- | --- | --- |
| El chat solo actualizaba el estado cuando escribía una predicción | Las consultas operativas también devuelven el estado actual | El contador y las sugerencias deben coincidir con la respuesta |
| La lista usaba una sola orden por producto | Usa la lista completa `ordenes` del servidor | Una orden aprobada reciente no debe ocultar otra pendiente |
| La mención del chat no tenía destino identificado | IDs verificados, enlace «Ver sugerencia», resaltado y etiqueta visible | Permite localizar la sugerencia sin interpretar texto del modelo |
| Cualquier estado distinto de aprobada ofrecía aprobar | Solo pendiente permite aprobar | Compatible con órdenes descartadas, emitidas, recibidas y pospuestas |

La mención se mantiene mientras la sugerencia siga pendiente. El chat deja de
ofrecer acciones sobre órdenes aprobadas. Las sugerencias mencionadas aparecen
primero, respetando paginación y aprobación individual. Repetir la predicción
del mismo producto y corte no recrea una orden ni revierte decisiones anteriores.

No se deducen órdenes de la prosa del modelo ni se habilita SQL libre. Las
restricciones del agente y el entrenamiento validado permanecen activos.

También se corrigió el lector de precios del presupuesto: reconoce las columnas
canónicas `precio_compra_centavos`, `lote_minimo` y `tasa_iva_pct`, manteniendo la
lectura del formato anterior en pesos. No se insertaron precios ficticios.

## Estado de Git inspeccionado

- Rama actual: `rama_zapta`, base `524b680`, con nuestras modificaciones locales.
- `origin/main` descargado: `8de49ea`, un commit posterior a esa base.
- Los cambios de ese commit todavía no están integrados en la rama actual.
- No hay archivos sin resolver en el índice ni marcadores de conflicto activos.

Se simuló la combinación de tres versiones en
`C:/Users/luisy/zenit-compatibilidad-20261123`, normalizando finales de línea para
no confundir CRLF de Windows con conflictos reales. Los archivos compartidos
`db.py`, `zenit_api.py`, la guía de instrucciones y `.gitignore` se combinaron sin
conflictos textuales. No se cambió de rama ni se hizo merge sobre el trabajo local.

## Fallos funcionales del commit descargado

La primera simulación ejecutó las pruebas actuales junto con las tres suites
nuevas del commit descargado en una copia del proyecto y de SQLite. Resultado:
**77 pruebas pasaron y tres fallaron**. No se usó la base operativa para esas
pruebas, que crean órdenes, recepciones y lecturas.

1. `test_alertas_caducidad_fefo`: la nueva consulta usa
   `cp.precio_compra_unitario`, pero la tabla creada por `db.init_db` contiene
   `precio_compra_centavos`. Produce `sqlite3.OperationalError` en una instalación
   con el esquema canónico. La consulta nueva debe usar el esquema real o una
   migración compatible antes de integrar ese módulo.
2. `test_catalogo_precios_cargado_en_db`: supone que ya existen 50 precios.
   El código descargado no los carga y la base copiada tenía cero precios.
   Debe preparar su fixture explícitamente o validar un catálogo real cargado.
3. `test_calculo_presupuesto_con_techo_semanal`: presupone precios positivos,
   por lo que falla con ese catálogo vacío. También necesita datos de prueba
   propios. Los tests nuevos utilizan la base global y deben aislarse con
   `tmp_path` antes de ejecutarlos sobre un entorno de trabajo.

Conclusión: la combinación textual es limpia, pero **todavía no se debe declarar
compatible la integración funcional de `8de49ea`**. No se integraron sus módulos
de recepciones/cadena de frío ni se ocultaron sus pruebas fallidas.

Se repitieron las tres suites nuevas con el código original de `origin/main`,
sin nuestras modificaciones, en otra copia aislada: **11 pasaron y fallaron las
mismas tres**. Estos fallos ya existen en el commit descargado; no los provocan
las restricciones del agente ni el entrenamiento o el resaltado nuevos.

## Comprobaciones del cambio actual

- Suite local de ZENIT: 67 pruebas pasaron antes de añadir seis regresiones de
  estados de órdenes; esas regresiones se comprobaron adicionalmente.
- Interfaz ZENIT: 44 pruebas pasaron; TypeScript y compilación de producción correctos.
- El backend no fue iniciado, detenido ni reiniciado durante esta revisión;
  las pruebas HTTP usan `TestClient` sin abrir un puerto.
