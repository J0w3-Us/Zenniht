# Guía de estructura y lógica de OpenJarvis

**Propósito:** entender el repositorio OpenJarvis antes de probarlo o adaptarlo a ZENIT.  
**Audiencia:** equipo mixto, desde quienes comienzan con OpenJarvis hasta quienes desarrollarán la adaptación.  
**Alcance:** describe la copia local en `OpenJarvis/`; no modifica su código ni configura proveedores. Los nombres de motores disponibles no significan que ya estén instalados, ejecutándose o conectados.

### Mapa rápido

OpenJarvis es un framework para asistentes de IA, no un único modelo ni un servidor de inferencia. Su flujo típico separa la interfaz, el agente que organiza el trabajo y el motor que envía la consulta al modelo:

```text
CLI o interfaz web
        ↓
API local (cuando se usa la GUI)
        ↓
Agente → contexto, instrucciones y herramientas
        ↓
Motor de inferencia → modelo local o proveedor remoto
        ↓
Respuesta y, si aplica, ejecución de herramientas, memoria y trazas
```

La predicción de inventario de ZENIT no forma parte de este flujo: el TFT debe calcularla directamente con `pytorch-forecasting`, localmente y en CPU. Si se reutiliza OpenJarvis, será la carcasa de interfaz/API, no el motor de predicción.

## 1. Estructura de OpenJarvis y función de sus partes

### Las cinco primitivas

La arquitectura documentada organiza el sistema en cinco primitivas. No son cinco programas que deban arrancarse por separado; son responsabilidades que colaboran durante una consulta.

| Primitiva | Responsabilidad | Dónde explorarla |
| --- | --- | --- |
| **Intelligence** | Describe modelos disponibles y sus características: identificadores, proveedores y motores compatibles. Es un catálogo y metadatos; no ejecuta por sí mismo el modelo. | [`src/openjarvis/intelligence/`](../../OpenJarvis/src/openjarvis/intelligence/) y [`model_catalog.py`](../../OpenJarvis/src/openjarvis/intelligence/model_catalog.py). |
| **Engine** | Adapta una interfaz común a distintos runtimes o proveedores de inferencia. Resuelve cuál motor usar y cómo enviarle solicitudes. | [`src/openjarvis/engine/`](../../OpenJarvis/src/openjarvis/engine/) y [`_discovery.py`](../../OpenJarvis/src/openjarvis/engine/_discovery.py). |
| **Agentic Logic** | Decide cómo atender una tarea: prepara mensajes, solicita respuestas al motor, puede llamar herramientas y vuelve a consultar hasta producir una respuesta final o alcanzar un límite. | [`src/openjarvis/agents/`](../../OpenJarvis/src/openjarvis/agents/). |
| **Memory** | Proporciona persistencia y recuperación de información para conversaciones, contexto o conectores. No equivale por sí sola a la base operativa de ventas de ZENIT. | [`src/openjarvis/memory/`](../../OpenJarvis/src/openjarvis/memory/) y [`src/openjarvis/tools/storage/`](../../OpenJarvis/src/openjarvis/tools/storage/). |
| **Learning** | Agrupa mecanismos de mejora/selección y experimentación del framework, normalmente a partir de resultados o trazas. No es el TFT de ZENIT. | [`src/openjarvis/learning/`](../../OpenJarvis/src/openjarvis/learning/). |

El resumen de estas primitivas y sus relaciones estaba originalmente en `docs/architecture/overview.md` y `docs/architecture/query-flow.md` del repositorio base OpenJarvis (carpetas retiradas al desacoplar OpenJarvis para ZENIT).

### Carpetas principales del repositorio

| Carpeta | Qué contiene y para qué sirve |
| --- | --- |
| [`src/openjarvis/core/`](../../OpenJarvis/src/openjarvis/core/) | Tipos, configuración, rutas y registros comunes utilizados por las demás capas. |
| [`src/openjarvis/intelligence/`](../../OpenJarvis/src/openjarvis/intelligence/) | Catálogo de modelos y sus metadatos. |
| [`src/openjarvis/engine/`](../../OpenJarvis/src/openjarvis/engine/) | Contratos y adaptadores para servidores locales, runtimes y servicios remotos. |
| [`src/openjarvis/agents/`](../../OpenJarvis/src/openjarvis/agents/) | Agentes integrados, ciclo de ejecución, orquestación y carga de instrucciones. |
| [`src/openjarvis/tools/`](../../OpenJarvis/src/openjarvis/tools/) | Herramientas que un agente puede invocar, ejecución/control de permisos y algunos almacenes. |
| [`src/openjarvis/memory/`](../../OpenJarvis/src/openjarvis/memory/) | Componentes de memoria y recuperación. |
| [`src/openjarvis/server/`](../../OpenJarvis/src/openjarvis/server/) | API HTTP/WebSocket que utiliza la interfaz web. No es el modelo. |
| [`src/openjarvis/cli/`](../../OpenJarvis/src/openjarvis/cli/) | Comandos `jarvis`, incluido el arranque de GUI, servidor, chat y agentes. |
| [`src/openjarvis/prompt/`](../../OpenJarvis/src/openjarvis/prompt/) | Construcción de prompts del sistema y contexto. |
| [`src/openjarvis/speech/`](../../OpenJarvis/src/openjarvis/speech/) | Reconocimiento y síntesis de voz (STT/TTS). |
| [`src/openjarvis/traces/`](../../OpenJarvis/src/openjarvis/traces/), [`telemetry/`](../../OpenJarvis/src/openjarvis/telemetry/) | Registro de ejecuciones y métricas. La telemetría y los destinos externos deben revisarse antes de una demo ZENIT sin Internet. |
| `configs/` *(retirada del repo)* | Configuraciones de ejemplo del repo base OpenJarvis. No usada por ZENIT. |
| [`frontend/`](../../OpenJarvis/frontend/) | Aplicación web React y TypeScript. |
| `rust/` *(retirada del repo)* | Extensiones nativas opcionales del framework base. No usada por ZENIT. |
| [`tests/`](../../OpenJarvis/tests/) | Pruebas del framework, separadas de las pruebas de datos de ZENIT en el nivel raíz. |

### Configuración y selección del motor

El cargador `load_config()` reúne la configuración de OpenJarvis. Puede recibir una ruta explícita; también reconoce `OPENJARVIS_CONFIG` y, si no se indican, busca la configuración predeterminada. `OPENJARVIS_HOME` (o `XDG_DATA_HOME`) influye en el directorio de datos/configuración del usuario. La implementación está en [`core/config.py`](../../OpenJarvis/src/openjarvis/core/config.py) y las rutas base en [`core/paths.py`](../../OpenJarvis/src/openjarvis/core/paths.py).

En términos generales:

- `[intelligence]` describe el modelo seleccionado, proveedor, ruta de modelo y parámetros de generación.
- `[engine]` elige el motor predeterminado.
- `[engine.<nombre>]` puede configurar opciones particulares del adaptador, como su host.
- El descubrimiento instancia los motores disponibles y consulta su estado; revisa [`engine/_discovery.py`](../../OpenJarvis/src/openjarvis/engine/_discovery.py).

Una configuración de modelo marcada como local no garantiza por sí sola que nunca haya tráfico de red: un motor puede apuntar a un host remoto o intentar una alternativa si el motor preferido no está disponible. Antes de usar OpenJarvis sin conexión hay que verificar el host efectivo y el comportamiento cuando falle el motor local.

## 2. Dónde viven los modelos y cómo se conectan

### Modelo, motor y servidor son cosas distintas

- **Modelo:** pesos o servicio de IA identificado por un nombre, por ejemplo, una familia/modelo del catálogo.
- **Motor:** adaptador que conoce el protocolo para enviar solicitudes a ese modelo.
- **Servidor de inferencia:** proceso que carga y sirve un modelo. Puede correr en la misma computadora o en otra.
- **Proveedor remoto:** servicio de un tercero que recibe solicitudes por Internet y puede requerir una clave.

Por eso, que un motor tenga un nombre conocido no indica dónde se ejecuta. La ubicación depende de su proceso y del `host` configurado.

### Familias de ejecución presentes en el código

| Tipo | Motores/ejemplos | Dónde ocurre la inferencia | Qué verificar |
| --- | --- | --- | --- |
| **Servidor local o compatible con API local** | Ollama y adaptadores compatibles con OpenAI para vLLM, SGLang, llama.cpp, MLX, LM Studio, Exo, Nexa, Uzu y otros. | En el proceso del servidor configurado. Puede estar en la misma máquina o en otra si el host apunta allí. | Que el servidor esté instalado y activo, que el host sea loopback/local cuando se requiera, y que el modelo exista/cargue. |
| **Inferencia local integrada o con ruta de pesos** | Apple Foundation Models y `gemma_cpp`, entre otros casos dependientes de plataforma. | En el dispositivo o proceso local, sujeto a disponibilidad de plataforma, runtime y archivos. | Sistema operativo compatible, extras instalados y ruta/artefactos locales. |
| **Servicio remoto** | `cloud`, `litellm` con proveedor remoto y `nim` configurado para un servicio externo. | Fuera de la computadora; usa una API de proveedor. | Conectividad, SDK/extra correspondiente, límites/costos del plan y credenciales. No es modo sin Internet. |

La lista concreta de adaptadores compatibles con OpenAI está en [`engine/openai_compat_engines.py`](../../OpenJarvis/src/openjarvis/engine/openai_compat_engines.py). Los motores `cloud`, `litellm` y `nim` tienen implementaciones separadas en [`cloud.py`](../../OpenJarvis/src/openjarvis/engine/cloud.py), [`litellm.py`](../../OpenJarvis/src/openjarvis/engine/litellm.py) y [`nim.py`](../../OpenJarvis/src/openjarvis/engine/nim.py).

### Catálogo, archivos y configuración

- El catálogo vive en [`intelligence/model_catalog.py`](../../OpenJarvis/src/openjarvis/intelligence/model_catalog.py); `ModelSpec` define metadatos y compatibilidad en [`core/types.py`](../../OpenJarvis/src/openjarvis/core/types.py).
- La configuración puede indicar `default_model`, `model_path`, `preferred_engine`, `provider` y parámetros de generación. La existencia de `model_path` en la configuración no significa que todos los motores carguen pesos desde esa ruta.
- Los ejemplos originales del repositorio base estaban en `configs/openjarvis/config.toml` (retirada al desacoplar OpenJarvis). Son ejemplos, no prueba de que esos modelos/servidores estén instalados o activos en el entorno actual.
- Los motores remotos pueden leer claves del entorno, por ejemplo `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY` o `NIM_API_KEY`, según el adaptador. No incluyas valores secretos en TOML versionado, capturas, CSV ni Git.

**Importante para pruebas:** un free tier sigue siendo una llamada a un proveedor remoto. Sirve para experimentos con Internet, pero no satisface el modo local/sin Internet exigido al prototipo ZENIT. Gemini, si el equipo decide estudiarlo aparte, no debe sustituir el TFT ni formar parte del flujo que se evalúa.

## 3. Frontend: piezas, pantallas y cómo cambiarlas

La GUI de navegador es una SPA de React/TypeScript. El directorio [`frontend/`](../../OpenJarvis/frontend/) contiene el código de interfaz; el backend expone la API local. Vite permite desarrollar el frontend y redirigir solicitudes API durante el desarrollo.

### De HTML a una pantalla

1. [`frontend/index.html`](../../OpenJarvis/frontend/index.html) declara el elemento raíz `#root`.
2. [`frontend/src/main.tsx`](../../OpenJarvis/frontend/src/main.tsx) prepara el tema y la URL de API y monta React con `BrowserRouter`, `ErrorBoundary` y `App`.
3. [`frontend/src/App.tsx`](../../OpenJarvis/frontend/src/App.tsx) registra las rutas, carga partes globales y compone la aplicación.
4. [`frontend/src/components/Layout.tsx`](../../OpenJarvis/frontend/src/components/Layout.tsx) dibuja el marco compartido: navegación lateral, contenido de la página, estado del sistema y avisos de aprobación.
5. La ruta seleccionada muestra una página de [`frontend/src/pages/`](../../OpenJarvis/frontend/src/pages/), compuesta por componentes reutilizables de `components/`.

### Pantallas y archivos relacionados

| Pantalla/área | Función actual | Dónde modificarla |
| --- | --- | --- |
| **Chat** (`/`) | Conversación, mensajes, entrada, streaming y herramientas. | [`pages/ChatPage.tsx`](../../OpenJarvis/frontend/src/pages/ChatPage.tsx), [`components/Chat/ChatArea.tsx`](../../OpenJarvis/frontend/src/components/Chat/ChatArea.tsx) y componentes cercanos como `InputArea` y `MessageBubble`. |
| **Dashboard** (`/dashboard`) | Panel de energía, comparación de costos y depuración de trazas. | [`pages/DashboardPage.tsx`](../../OpenJarvis/frontend/src/pages/DashboardPage.tsx) y [`components/Dashboard/`](../../OpenJarvis/frontend/src/components/Dashboard/). |
| **Data Sources** (`/data-sources`) | Conectores y fuentes de información. | `pages/DataSourcesPage.tsx` y el cliente de conectores en `src/lib/connectors-api.ts`. |
| **Agents** (`/agents`) | Agentes, ejecuciones, herramientas y actividad relacionada. | `pages/AgentsPage.tsx` y componentes que importa. |
| **Logs** (`/logs`) | Eventos y registros visibles en la aplicación. | `pages/LogsPage.tsx`. |
| **Settings** (`/settings`) | Preferencias, tema y opciones del entorno/proveedor. | `pages/SettingsPage.tsx`. |
| **Get Started** (`/get-started`) | Guía y estado inicial de conexión. | `pages/GetStartedPage.tsx`. |
| **Navegación común** | Enlaces, búsqueda de conversaciones, tema y controles laterales. | [`components/Sidebar/Sidebar.tsx`](../../OpenJarvis/frontend/src/components/Sidebar/Sidebar.tsx) y `components/Layout.tsx`. |

Las rutas se declaran en `App.tsx`; la navegación visible se declara en `components/Sidebar/Sidebar.tsx`. Para añadir una pantalla nueva, hay que actualizar ambas y crear su página. No basta con crear un archivo en `pages/` si no existe una ruta/enlace que lo use.

### API, estado y estilos

- [`src/lib/api.ts`](../../OpenJarvis/frontend/src/lib/api.ts) centraliza llamadas HTTP generales, URL base y cabeceras; [`src/lib/connectors-api.ts`](../../OpenJarvis/frontend/src/lib/connectors-api.ts) cubre el dominio de conectores.
- [`src/lib/store.ts`](../../OpenJarvis/frontend/src/lib/store.ts) mantiene estado compartido con Zustand y persistencia local del navegador. `hooks/` agrupa hooks; `types/` contiene tipos compartidos entre pantallas.
- [`src/components/ui/`](../../OpenJarvis/frontend/src/components/ui/) contiene primitivas de interfaz; `components/Desktop/` y `components/setup/` agrupan piezas específicas del entorno de escritorio o configuración.
- [`src/index.css`](../../OpenJarvis/frontend/src/index.css) define estilos globales y variables de tema claro/oscuro. Es el lugar común para ajustar tokens visuales; las páginas/componentes también pueden usar utilidades Tailwind.
- [`vite.config.ts`](../../OpenJarvis/frontend/vite.config.ts) configura plugins, alias, salida de build y proxy de desarrollo. El destino del proxy puede depender de `OPENJARVIS_VITE_PROXY_TARGET` o `VITE_API_URL`; sin esas variables usa el destino local predeterminado del proyecto.

### Cómo adaptar una pantalla al tablero ZENIT

1. Decide si la nueva tabla corresponde a una ruta propia o reemplaza la pantalla Dashboard. Mantén navegación y página coordinadas.
2. Crea un componente de presentación pequeño para la tabla de 50 productos; muestra explícitamente estados de carga, error y datos vacíos.
3. Define tipos TypeScript para la respuesta de inventario/alertas y funciones API específicas en `src/lib/api.ts` (o en un cliente de dominio separado).
4. No calcules probabilidades en React: la interfaz debe mostrar la salida del backend/TFT. Resalta en rojo únicamente el estado de desabasto definido por el prototipo.
5. Centraliza colores y estados visuales en los tokens/estilos compartidos para que la alerta sea consistente y legible.
6. Agrega pruebas a la página/componente para el número de filas, error/carga y marcado de productos; ejecuta Vitest y build.

Comandos de frontend desde `OpenJarvis/frontend/`:

```powershell
npm run dev
npm test
npm run build
```

El proyecto declara Node `>=22.22` y npm `>=11.19`. `npm run build` corre TypeScript y Vite; según la configuración, el resultado se coloca bajo `src/openjarvis/server/static/`, por lo que un build cambia artefactos generados dentro del repositorio. Revisa el estado de Git después de compilar y no conserves cambios generados que no sean parte del trabajo.

## 4. Lógica de OpenJarvis: CLI, agente, voz e instrucciones

### CLI y GUI no son el agente

La CLI usa Click. Su registro está en [`src/openjarvis/cli/__init__.py`](../../OpenJarvis/src/openjarvis/cli/__init__.py), y el entry point `jarvis` se declara en [`pyproject.toml`](../../OpenJarvis/pyproject.toml).

| Comando | Qué hace |
| --- | --- |
| `jarvis ask` | Consulta puntual: prepara la configuración/insumos del agente y devuelve una respuesta. Algunas opciones permiten seleccionar agente o evitar el ciclo completo de agente. Implementación en [`cli/ask.py`](../../OpenJarvis/src/openjarvis/cli/ask.py). |
| `jarvis chat` | Conversación interactiva con historial y opciones de agente, herramientas, instrucciones y voz. Implementación en [`cli/chat_cmd.py`](../../OpenJarvis/src/openjarvis/cli/chat_cmd.py). |
| `jarvis agents` | Administra agentes persistentes, por ejemplo crearlos, listarlos o ejecutar/pausar tareas. Implementación en [`cli/agent_cmd.py`](../../OpenJarvis/src/openjarvis/cli/agent_cmd.py). |
| `jarvis gui` | Arranca el frontend y, si corresponde, el servidor API local; puede abrir el navegador. Es un lanzador, no una estrategia de agente. Implementación en [`cli/gui_cmd.py`](../../OpenJarvis/src/openjarvis/cli/gui_cmd.py). |
| `jarvis serve` | Inicia el servidor de API; los comandos y rutas del servidor están en `cli/serve.py` y `src/openjarvis/server/`. |

El frontend consume la API del backend; el agente se ejecuta detrás de esa API. Por eso, cambiar el texto de un botón no cambia la lógica del agente, y cambiar un prompt no crea una ruta nueva en la interfaz.

### Ciclo del agente: razonamiento y herramientas

El contrato base para agentes y resultados está en [`agents/_stubs.py`](../../OpenJarvis/src/openjarvis/agents/_stubs.py). Ejemplos:

- **Orchestrator:** [`agents/orchestrator.py`](../../OpenJarvis/src/openjarvis/agents/orchestrator.py) puede enviar mensajes al motor, recibir llamadas a herramientas, ejecutarlas e incorporar resultados para otra vuelta. Repite hasta una respuesta final o un límite de turnos.
- **Native ReAct:** [`agents/native_react.py`](../../OpenJarvis/src/openjarvis/agents/native_react.py) implementa un estilo explícito de pensamiento/acción/observación.
- **Agentes persistentes:** [`agents/executor.py`](../../OpenJarvis/src/openjarvis/agents/executor.py) ejecuta ticks/tareas y gestiona eventos y trazas. Otros agentes, como el proactivo, pueden proponer acciones.
- **Herramientas:** `ToolExecutor` valida y ejecuta herramientas con capacidades y límites; sus contratos están en [`tools/_stubs.py`](../../OpenJarvis/src/openjarvis/tools/_stubs.py). Algunas acciones pueden exigir confirmación.
- **Aprobaciones:** [`tools/approval_store.py`](../../OpenJarvis/src/openjarvis/tools/approval_store.py) conserva acciones pendientes y permisos recordados; [`server/approval_routes.py`](../../OpenJarvis/src/openjarvis/server/approval_routes.py) expone operaciones de decisión para clientes.
- **Memoria y contexto:** el chat puede recuperar/injectar contexto; [`tools/storage/context.py`](../../OpenJarvis/src/openjarvis/tools/storage/context.py) maneja parte del contexto recuperable. Esto no sustituye un historial operacional fiable de existencias/ventas.

No se debe asumir que cualquier invocación ofrece aprobación humana segura: el camino de `ask` configura una función de confirmación automática para herramientas. Para una orden de compra de ZENIT, la aplicación debe presentar la propuesta y requerir una aprobación humana explícita; no debe permitir que un agente compre ni pague automáticamente.

### Prompts e instrucciones del agente

El prompt no necesariamente es una sola cadena fija. [`prompt/builder.py`](../../OpenJarvis/src/openjarvis/prompt/builder.py) construye el prompt del sistema a partir de una plantilla, prefijos configurados y contexto aplicable; puede incorporar archivos de persona (`SOUL.md`, `MEMORY.md`, `USER.md`) y skills. La configuración de agente, prompt y archivos de memoria se define en [`core/config.py`](../../OpenJarvis/src/openjarvis/core/config.py).

Algunos agentes cargan plantillas/ejemplos desde directorios de agentes bajo `OPENJARVIS_HOME`; consulta [`agents/prompt_loader.py`](../../OpenJarvis/src/openjarvis/agents/prompt_loader.py). La configuración de ejemplo original en `configs/openjarvis/config.toml` seleccionaba un agente para ese ejemplo; no implica que todos los entornos usen el mismo.

Para ZENIT, cualquier instrucción conversacional debe quedar separada de reglas de negocio comprobables. El prompt puede ayudar a explicar una alerta, pero no debe crear etiquetas, modificar la predicción TFT, alterar la evaluación F1 ni inventar órdenes/cantidades.

### Voz: entrada (STT) y salida (TTS)

La voz es una capacidad opcional, separada del cálculo del agente y de la interfaz:

- **STT (Speech-to-Text):** [`speech/_discovery.py`](../../OpenJarvis/src/openjarvis/speech/_discovery.py) busca backends. La configuración puede elegir Faster-Whisper local o servicios como OpenAI/Deepgram, estos últimos con credenciales.
- **TTS (Text-to-Speech):** [`speech/_tts_discovery.py`](../../OpenJarvis/src/openjarvis/speech/_tts_discovery.py) descubre backends como Kokoro local y opciones de proveedores externos.
- **Captura/reproducción:** [`speech/voice_io.py`](../../OpenJarvis/src/openjarvis/speech/voice_io.py) gestiona entrada/salida de audio; [`cli/_voice_chat.py`](../../OpenJarvis/src/openjarvis/cli/_voice_chat.py) conecta voz con el chat interactivo.
- **Configuración y dependencias:** los campos de backend/voz están en `core/config.py`; los extras correspondientes están en `pyproject.toml` bajo `speech`, `voice`, `desktop` y extras de proveedores.

Una función presentada como “voz” no es necesariamente offline: hay que confirmar qué backend se seleccionó, si descarga modelos al primer uso y si tiene una ruta de fallback a servicios externos. La voz no es necesaria para el hito de entrada/procesamiento de ZENIT y debe mantenerse opcional.

### Recomendación de límites para la adaptación

Para que las pruebas no mezclen responsabilidades:

```text
CSV → SQLite → TFT local (CPU) → resultado por producto
                                  ↓
                    API local y tabla de 50 productos
                                  ↓
                      aprobación humana de la orden
```

- Mantén la predicción y sus métricas fuera del bucle de conversación y de los motores LLM de OpenJarvis.
- Reutiliza únicamente la interfaz/API que demuestre ser útil; elimina del flujo de la demo las rutas no necesarias, proveedores externos y claves.
- Si más adelante se agrega un agente de explicación, que consuma resultados ya calculados y no pueda alterar datos, pronósticos ni compras.
- Conserva los permisos humanos para acciones con efectos y verifica que el código de aprobación que se usa realmente requiera confirmación explícita.
- En las primeras pruebas, valida por separado carga del CSV (4,500 filas), inferencia TFT de 50 productos y representación de exactamente 50 filas. La GUI genérica de OpenJarvis, por sí sola, no demuestra esos hitos.

La guía describe módulos y rutas existentes, no la disponibilidad de un modelo ni un endpoint en la computadora. La presencia de un adaptador en el código no demuestra que se haya configurado o que funcione sin Internet.
