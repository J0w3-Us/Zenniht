# Manual de Operación y Referencia Local de ZENIT

Este documento es una guía práctica (**How-To / Referencia técnica**) para desarrolladores, operadores y agentes de IA. Describe cómo preparar, ejecutar y validar el sistema ZENIT en un entorno 100% local y sin conexión a Internet.

---

## 1. Requisitos Previos y Entorno

- **Sistema Operativo:** Windows, Linux o macOS.
- **Python:** Entorno virtual `.venv` con las dependencias fijadas en `OpenJarvis/requirements.txt` (PyTorch CPU, `pytorch-forecasting`, FastAPI, Uvicorn, pytest).
- **Node.js:** Versión `>=22.22` con `npm` (`>=11.19.0`), según `OpenJarvis/frontend/package.json`.
- **Costo Financiero:** **0.00 MXN** (sin dependencias en la nube ni APIs comerciales requeridas durante la ejecución).

> **Importante:** Todos los comandos del backend, datos, modelo y pruebas se ejecutan dentro de la carpeta `OpenJarvis/`, **no** desde la raíz del repositorio. No instales `OpenJarvis/pyproject.toml` (pertenece al proyecto base OpenJarvis); usa únicamente `OpenJarvis/requirements.txt`.

---

## 2. Preparación Única del Entorno

### Backend y modelo (Python)
```powershell
cd OpenJarvis
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
*(En Windows PowerShell, si el sistema bloquea scripts `.ps1`, ejecuta una sola vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.)*

### Frontend (Node.js)
```powershell
cd OpenJarvis\frontend
npm install
```

### Agente conversacional local (Ollama)
Para usar el chat principal del **Agente ZENIT** 100% local (sin API keys ni créditos):
1. Instala **Ollama** desde `https://ollama.com` y asegúrate de que esté corriendo en `http://127.0.0.1:11434`.
2. Descarga un modelo ligero compatible con *tool calling* (recomendado `qwen2.5:3b`):
```powershell
ollama pull qwen2.5:3b
```
*(El agente usa Ollama únicamente para orquestar consultas de solo lectura en SQLite y disparar el TFT local; nunca reemplaza al TFT ni aprueba órdenes automáticamente.)*

---

## 3. Flujo de Ejecución Rápida (Paso a Paso)

Ejecuta los pasos 1 a 4 desde la carpeta `OpenJarvis/` con el entorno virtual `.venv` activo:

### Paso 1: Generar los Datos Canónicos Sintéticos
Genera el archivo `data/ventas.csv` y la base de datos `data/zenith.db` con semilla fija (50 productos × 90 días = 4,500 registros):
```powershell
python data\generar_datos.py
```

### Paso 2: Entrenar y Configurar Modelos (TFT y LLM Ollama)
El script de entrenamiento soporta tanto el modelo predictivo de series temporales como la configuración del modelo conversacional con el prompt externo:

```powershell
# A) Entrenar Temporal Fusion Transformer (TFT)
python -m modelo.entrenar_tft tft --epochs 45 --hidden-size 16 --evaluar

# B) Acondicionar modelo local en Ollama con el prompt oficial de Zenit
python -m modelo.entrenar_tft ollama --base qwen2.5:3b --nombre zenit

# C) Modo directo compatible por defecto
python -m modelo.entrenar_tft --epochs 45 --evaluar
```

> **Selección Automática de IA:**  
> Cuando el usuario no especifica un modelo, el backend detecta automáticamente los modelos disponibles en Ollama (`http://127.0.0.1:11434`) y selecciona el óptimo según esta prioridad:
> 1. Modelo solicitado explícitamente en el chat (si está instalado).
> 2. Variable de entorno `ZENIT_OLLAMA_MODEL` (si está definida).
> 3. Modelo personalizado `zenit` (generado por `entrenar_tft.py ollama`).
> 4. Modelos recomendados: `qwen2.5:3b` > `qwen2.5:7b` > `llama3.2:3b` > `llama3.1:8b` > `mistral:7b`.
> 5. Si ninguno coincide, selecciona automáticamente el primer modelo disponible en Ollama.

### Paso 3: Ejecutar la Suite de Pruebas Automatizadas
Verifica el universo cerrado, SQLite, el modelo TFT y la API local:
```powershell
python -m pytest -q --noconftest tests\zenit
```
*(Se usa `--noconftest` para evitar cargar `tests/conftest.py` heredado de OpenJarvis, que requiere dependencias externas no usadas por ZENIT.)*

Para medir el tiempo de inferencia en CPU (30 lotes de 50 productos + calentamiento):
```powershell
python -m modelo.medir_rendimiento
```

### Paso 4: Iniciar el Backend de la API Local
Inicia el servidor local de FastAPI en el puerto 8000:
```powershell
python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000
```
> Endpoints clave disponibles:
> - `GET /api/zenit/estado` - Devuelve existencias del último corte y alertas activas.
> - `POST /api/zenit/cargar` / `POST /api/zenit/cargar-local` - Valida y carga el CSV canónico en SQLite.
> - `POST /api/zenit/predecir` - Ejecuta la inferencia TFT para una fecha de corte dada.
> - `POST /api/zenit/ordenes/{id}/aprobar` - Aprueba manualmente una orden sugerida.

### Paso 5: Iniciar la Interfaz Web (Vite + React)
En una terminal separada, accede a `OpenJarvis\frontend` y levanta el entorno de desarrollo:
```powershell
cd OpenJarvis\frontend
npm run dev
```
La aplicación abrirá automáticamente en: `http://localhost:5173/zenit`

---

## 4. Matriz de Errores Comunes y Soluciones

| Síntoma o Error | Causa Probable | Solución Inmediata |
|---|---|---|
| *"No se pudo conectar con la API local de ZENIT"* | El servidor FastAPI de `zenit_api.py` no está corriendo en el puerto 8000. | Ejecutar desde `OpenJarvis/`: `python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000`. |
| *"No se encontró el checkpoint TFT"* | No se ha ejecutado el entrenamiento inicial de la red. | Correr desde `OpenJarvis/`: `python -m modelo.entrenar_tft` para generar `modelo/zenith_tft.ckpt`. |
| *"Fallo en prueba de coincidencia CSV/SQLite"* | La base de datos `data/zenith.db` no existe o está desincronizada. | Regenerar el dataset ejecutando desde `OpenJarvis/`: `python data\generar_datos.py`. |
| *"ModuleNotFoundError: No module named 'openjarvis'" en pytest* | Pytest cargó `tests/conftest.py` heredado de OpenJarvis. | Ejecutar `python -m pytest -q --noconftest tests\zenit`. |
| *"La ejecución de scripts está deshabilitada"* en PowerShell | Política de ejecución de Windows bloquea `npm.ps1` / `Activate.ps1`. | Ejecutar `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` o usar `npm.cmd`. |
| *"Error de CORS en el navegador"* | La llamada web se hace fuera del proxy de Vite o del puerto correcto. | Acceder exclusivamente a través de `http://localhost:5173/zenit` y comprobar `vite.config.ts`. |
