# Manual de Operación y Referencia Local de ZENIT

Este documento es una guía práctica (**How-To / Referencia técnica**) para desarrolladores, operadores y agentes de IA. Describe cómo preparar, ejecutar y validar el sistema ZENIT en un entorno 100% local y sin conexión a Internet.

---

## 1. Requisitos Previos y Entorno

- **Sistema Operativo:** Windows, Linux o macOS.
- **Python:** 3.10 a 3.12 (con soporte para PyTorch CPU).
- **Node.js:** Versión 20+ con `npm`.
- **Costo Financiero:** **0.00 MXN** (sin dependencias en la nube ni APIs comerciales requeridas).

---

## 2. Flujo de Ejecución Rápida (Paso a Paso)

Ejecuta los siguientes comandos desde la raíz del proyecto `Zenith-Openjarvis`:

### Paso 1: Generar los Datos Canónicos Sintéticos
Genera el archivo `data/ventas.csv` y la base de datos `data/zenith.db` con semilla fija (50 productos × 90 días = 4,500 registros):
```powershell
python data\generar_datos.py
```

### Paso 2: Entrenar o Validar el Modelo Predictivo (TFT)
Entrena el modelo Temporal Fusion Transformer en CPU local (genera el checkpoint `modelo/zenith_tft.ckpt`):
```powershell
python -m modelo.entrenar_tft
```

### Paso 3: Ejecutar la Suite de Pruebas Automatizadas
Verifica la integridad de las 8 columnas del dataset, la distribución Kraljic y la coincidencia con SQLite:
```powershell
python -m pytest -q tests\zenit
```

### Paso 4: Iniciar el Backend de la API Local
Inicia el servidor local de FastAPI en el puerto 8000:
```powershell
python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000
```
> Endpoints clave disponibles:
> - `GET /api/zenit/estado` - Devuelve existencias del último corte y alertas activas.
> - `POST /api/zenit/predecir` - Ejecuta la inferencia TFT para una fecha de corte dada.
> - `POST /api/zenit/ordenes/{id}/aprobar` - Aprueba manualmente una orden sugerida.

### Paso 5: Iniciar la Interfaz Web (Vite + React)
En una terminal separada, accede a la carpeta del frontend y levanta el entorno de desarrollo:
```powershell
cd OpenJarvis\frontend
npm run dev
```
La aplicación abrirá automáticamente en: `http://localhost:5173/zenit`

---

## 3. Matriz de Errores Comunes y Soluciones

| Síntoma o Error | Causa Probable | Solución Inmediata |
|---|---|---|
| *"No se pudo conectar con la API local de ZENIT"* | El servidor FastAPI de `zenit_api.py` no está corriendo en el puerto 8000. | Ejecutar `python -m uvicorn zenit_api:app --host 127.0.0.1 --port 8000`. |
| *"Checkpoint TFT no encontrado"* | No se ha ejecutado el entrenamiento inicial de la red. | Correr `python -m modelo.entrenar_tft` para generar `modelo/zenith_tft.ckpt`. |
| *"Fallo en prueba de coincidencia CSV/SQLite"* | La base de datos `zenith.db` no existe o está desincronizada. | Regenerar el dataset ejecutando `python data/generar_datos.py`. |
| *"Error de CORS en el navegador"* | La llamada web se hace fuera del proxy de Vite o del puerto correcto. | Acceder exclusivamente a través de `http://localhost:5173/zenit` o comprobar el proxy en `vite.config.ts`. |
