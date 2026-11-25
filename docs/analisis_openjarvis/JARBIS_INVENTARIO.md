# Inventario de OpenJarvis para el prototipo ZENIT

**Fecha:** 13 de noviembre de 2026  
**Alcance:** Paso 0 del plan de armado. Solo inspección y documentación; no se modificó código ni configuración.

## Resumen ejecutivo

La carpeta `OpenJarvis/` contiene un framework de asistente personal de propósito general, no una aplicación de farmacia. Su núcleo combina Python, módulos Rust y una interfaz web React/TypeScript. Incluye chat y agentes, proveedores de modelos, búsquedas, canales de mensajería, conectores, telemetría y opciones de despliegue. La mayoría de esas funciones no corresponde al prototipo ZENIT y algunas dependen de Internet o de credenciales.

El proyecto raíz ya contiene el generador y las pruebas de la Sección 1. El `data/ventas.csv` actual tiene las ocho columnas acordadas, 4,500 filas, 50 productos y 90 fechas. `data/zenith.db` todavía no está creado; el generador lo escribe al ejecutarse.

## Lenguaje, framework y estructura

| Componente | Evidencia y observación |
| --- | --- |
| Backend y lógica | Python 3.10–3.13 (`OpenJarvis/pyproject.toml`); paquete `src/openjarvis/`. |
| Interfaz | React 19, TypeScript, Vite y Tailwind (`OpenJarvis/frontend/package.json`). La GUI inicia una API local y la interfaz web. |
| Extensión nativa | Rust mediante `OpenJarvis/rust/`; el `Makefile` compila la extensión Python con `maturin`. |
| Servidor | FastAPI/Uvicorn están en el extra `server` de `pyproject.toml`, no en las dependencias mínimas de ZENIT. |
| Pruebas | Pytest en `OpenJarvis/tests/`; además, `tests/test_seccion1.py` en la raíz valida restricciones de los datos. |
| Tamaño observado | Aproximadamente 2,240 archivos dentro de `OpenJarvis/`; entre los tipos principales hay Python, TOML, Rust, Markdown y TypeScript/TSX. |

Carpetas relevantes de OpenJarvis:

- `src/openjarvis/`: CLI, agentes, servidor, motores de inferencia, herramientas, canales, conectores, telemetría y almacenamiento.
- `frontend/`: aplicación web y componentes de escritorio.
- `rust/`: extensiones nativas.
- `configs/`: configuración de la aplicación.
- `deploy/`: Docker y configuraciones de servicios/plataformas.
- `examples/`: ejemplos de asistentes e integraciones.
- `tests/`: pruebas del framework.
- `docs/`: documentación de OpenJarvis.

En la raíz del proyecto ZENIT:

- `data/generar_datos.py`: genera el CSV y la base SQLite local; usa semilla fija.
- `data/ventas.csv`: dataset actual, verificado con 4,500 filas, 50 productos y 90 fechas.
- `tests/test_seccion1.py`: valida columnas, universo, distribución Kraljic, nulos, quiebres y coincidencia con SQLite.
- `requirements.txt`: dependencias propuestas para el prototipo; incluye NumPy, pandas, scikit-learn, PyTorch, Lightning, `pytorch-forecasting` y pytest.

## Dependencias

`OpenJarvis/pyproject.toml` declara un conjunto amplio de dependencias base, entre ellas `openai`, `httpx`, `ddgs`, `posthog`, `datasets` y clientes de canales. Declara extras para inferencia en nube (OpenAI/Anthropic y Google), servidor web, escritorio, mensajería, búsqueda, voz, conectores, métricas y otras funciones.

La GUI requiere Node.js 22+ y npm 11+ según el README y `frontend/package.json`. El flujo de desarrollo descrito por el proyecto usa `uv`; el `Makefile` ofrece `make setup`, `make build`, `make test` y `make lint`. El setup/build completos incluyen dependencias del framework y la extensión Rust, no solo las del modelo de ZENIT.

El `requirements.txt` de la raíz está orientado al modelo TFT, pero todavía no declara dependencias del backend de OpenJarvis. Si se reutiliza el servidor, primero habrá que decidir qué parte se conserva y agregar solo las dependencias necesarias, compatibles con el requisito de software libre y ejecución local.

## APIs externas, nube y costo

La configuración y el código de OpenJarvis contemplan varios servicios externos:

- Proveedores de modelos por API —por ejemplo OpenAI y Anthropic— y extras para proveedores de Google.
- Búsqueda web, integraciones OAuth y canales externos como mensajería.
- PostHog para analítica/telemetría y funciones de evaluación/integración con servicios externos.
- Instaladores y documentación de despliegue que descargan software o modelos desde Internet.

Esto describe capacidades disponibles en el framework; no implica que todas se activen en cada ejecución. Sin embargo, la presencia de esas rutas, dependencias y configuraciones significa que no se debe asumir que una instalación estándar cumple por sí sola el costo cero o el modo sin Internet. El flujo de instalación recomendado en el README también requiere Internet.

## Claves y archivos `.env`

- No se encontró un `.env` en la raíz del proyecto ZENIT.
- OpenJarvis incluye `deploy/docker/.env.example`; es una plantilla, no evidencia de credenciales reales.
- El código admite credenciales por variables de entorno para proveedores y canales (por ejemplo, claves de proveedores de IA o tokens de mensajería). La configuración Docker también solicita `OPENJARVIS_API_KEY`.
- `.gitignore` de la raíz excluye `.env`; esto debe mantenerse. No se deben copiar secretos al prototipo ni mostrar o versionar valores de credenciales.

## Persistencia y bases de datos

- OpenJarvis usa SQLite en distintos almacenes locales separados, entre ellos memoria, trazas, telemetría, sesiones, conectores y aprobaciones; las rutas predeterminadas están bajo la configuración local del usuario.
- Existe una herramienta del framework que puede consultar PostgreSQL; no es necesaria para ZENIT y deberá quedar fuera del flujo del prototipo.
- El generador de ZENIT crea `data/zenith.db`, una SQLite con la tabla `ventas` y clave primaria `(producto, fecha)`.
- En esta inspección no existe `data/zenith.db`. La prueba `test_sqlite_coincide_con_el_csv` la requiere, por lo que se debe ejecutar `python data/generar_datos.py` antes de correr la prueba completa.

## Arranque conocido

El README de OpenJarvis presenta `jarvis` como comando de chat y `jarvis gui` como comando para iniciar la interfaz gráfica y su API local. La GUI necesita Node.js 22+ y el frontend disponible. Para desarrollo, el repositorio documenta `uv sync --extra dev`, y su `Makefile` configura extras adicionales, compila Rust y ejecuta pruebas.

Estos comandos describen el arranque de OpenJarvis, no el de ZENIT. No se verificó que el prototipo arranque sin Internet; de hecho, el instalador sugerido descarga componentes y el framework ofrece integraciones remotas. La ejecución offline deberá comprobarse cuando se defina qué dependencias y módulos se conservarán.

## Licencia

`OpenJarvis/LICENSE` contiene la **Apache License 2.0**. Debe conservarse con el proyecto y respetarse al redistribuirlo: incluir la licencia, conservar avisos de copyright/atribución aplicables y señalar los archivos modificados cuando corresponda. No reemplazar ni eliminar la licencia de OpenJarvis.

## Propuesta para revisión del equipo

| Decisión | Propuesta |
| --- | --- |
| **Conservar** | `OpenJarvis/LICENSE` y avisos aplicables; solo la estructura o componentes locales que efectivamente se reutilicen (por ejemplo, servidor/UI si resultan más simples que sustituirlos); generador, CSV de 4,500 filas y pruebas de la Sección 1. |
| **Reemplazar/adaptar** | La experiencia genérica de chat/agentes por el flujo de farmacia de ZENIT; persistencia para el dataset en SQLite local; lógica de predicción por TFT local con `pytorch-forecasting`, `hidden_size=16`, CPU y horizonte de 7 días; salida limitada a 50 productos y órdenes sugeridas que aprueba el dueño. |
| **Retirar del prototipo** | Rutas y dependencias de modelos en nube, búsqueda web, analítica remota, conectores OAuth, canales de mensajería, despliegues externos y funciones ajenas al desabasto. Conviene deshabilitarlos o excluirlos del producto final, no borrar archivos upstream indiscriminadamente antes de acordar el alcance y revisar avisos de licencia. |

## Riesgo principal y siguiente decisión

La restricción más delicada es **local y sin Internet, con costo cero**: OpenJarvis tiene proveedores externos, analítica, credenciales e instaladores con descargas dentro de su ecosistema. Antes de reutilizar su arranque hay que identificar y aislar esas rutas, además de asegurar de antemano las dependencias necesarias para la laptop de demostración. La opción concreta de conservar el backend/UI debe decidirse con el equipo tras revisar este inventario; hasta entonces no se ha modificado el código.

## Verificación realizada

- Lectura de `CLAUDE.md` y de todos los documentos que existían en `docs/` antes de escribir este inventario.
- Inspección estática de estructura, README, manifiestos, licencia, Makefile, generador y prueba de Sección 1.
- Verificación de forma del CSV actual: 4,500 filas, 50 productos, 90 fechas y las ocho columnas esperadas.
- No se ejecutó `pytest`: es un cambio documental del Paso 0 y falta `data/zenith.db`, que la suite actual espera. No se generó la base porque eso modificaría/crearía un artefacto de datos fuera del inventario.
