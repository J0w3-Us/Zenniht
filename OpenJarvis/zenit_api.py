"""API local de ZENIT para carga, inferencia TFT y aprobación de órdenes."""
import hashlib
import hmac
import logging
import sqlite3
from datetime import date
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from agente_zenit import ejecutar_chat_agente, obtener_estado_ollama
from kraljic import ordenar_alertas_kraljic

CSV_PATH = db.CSV_PATH
DB_PATH = db.DB_PATH
UMBRAL_ALERTA = 0.50
UMBRAL_INFERENCIA_MS = 1000

logger = logging.getLogger("zenit")
app = FastAPI(title="ZENIT local", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class SolicitudPrediccion(BaseModel):
    fecha_corte: date = date(2026, 10, 22)


class TurnoChat(BaseModel):
    role: str
    content: str


class SolicitudChatAgente(BaseModel):
    mensaje: str
    historial: List[TurnoChat] = []
    modelo: Optional[str] = None
    fecha_corte: date = date(2026, 10, 22)


def _predecir_lote(fecha_corte: str) -> Tuple[List[Dict[str, object]], float]:
    from modelo.predecir import predecir_lote

    return predecir_lote(fecha_corte)


def _obtener_estado() -> Dict[str, object]:
    db.init_db(DB_PATH)
    conn = db.get_connection(DB_PATH)
    filas = conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
    productos_db = conn.execute(
        "SELECT producto, cuadrante_kraljic FROM ventas "
        "GROUP BY producto, cuadrante_kraljic"
    ).fetchall()
    fecha_existencia = conn.execute("SELECT MAX(fecha) FROM ventas").fetchone()[0]
    existencias_db = conn.execute(
        "SELECT producto, existencia FROM ventas WHERE fecha = ?",
        (fecha_existencia,),
    ).fetchall() if fecha_existencia else []
    conn.close()

    existencia_por_producto = {
        fila["producto"]: int(fila["existencia"])
        for fila in existencias_db
    }
    cargado = (
        filas == 4500
        and len(productos_db) == 50
        and len(existencias_db) == 50
        and set(existencia_por_producto) == {fila["producto"] for fila in productos_db}
    )
    predicciones = db.obtener_predicciones(DB_PATH) if cargado else []
    ordenes = db.obtener_ordenes(DB_PATH) if cargado else []
    prediccion_por_producto = {p["producto"]: p for p in predicciones}
    orden_por_producto = {}
    for orden in ordenes:
        orden_por_producto.setdefault(orden["producto"], orden)

    productos = []
    if cargado:
        for fila in productos_db:
            prediccion = prediccion_por_producto.get(fila["producto"])
            productos.append({
                "producto": fila["producto"],
                "cuadrante_kraljic": fila["cuadrante_kraljic"],
                "existencia": existencia_por_producto[fila["producto"]],
                "probabilidad": prediccion["probabilidad"] if prediccion else None,
                "en_desabasto": bool(prediccion["en_desabasto"]) if prediccion else None,
                "orden": orden_por_producto.get(fila["producto"]),
            })
        productos = ordenar_alertas_kraljic([
            {**producto, "probabilidad": producto["probabilidad"] or 0.0}
            for producto in productos
        ])
        for producto in productos:
            if producto["producto"] not in prediccion_por_producto:
                producto["probabilidad"] = None
                producto["en_desabasto"] = None

    inferencia: Optional[Dict[str, object]] = None
    if predicciones:
        ultima = predicciones[0]
        inferencia = {
            "fecha_corte": ultima["fecha_corte"],
            "tiempo_inferencia_ms": ultima["tiempo_inferencia_ms"],
            "cumple_umbral_tiempo": (
                float(ultima["tiempo_inferencia_ms"]) < UMBRAL_INFERENCIA_MS
            ),
        }

    return {
        "datos_cargados": cargado,
        "filas": filas,
        "fecha_existencia": fecha_existencia if cargado else None,
        "productos": productos,
        "ordenes": ordenes,
        "inferencia": inferencia,
    }


def _cargar_csv_canonico() -> Dict[str, object]:
    if not CSV_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"No se encontró el dataset local: {CSV_PATH}",
        )
    try:
        resultado = db.cargar_csv(CSV_PATH, DB_PATH)
    except (OSError, sqlite3.Error, ValueError) as exc:
        logger.exception("No se pudo cargar el dataset ZENIT.")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo cargar el CSV: {exc}",
        ) from exc

    logger.info("%s", resultado["mensaje"])
    return resultado


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "modo": "local"}


@app.post("/api/zenit/cargar")
async def cargar_dataset(request: Request) -> Dict[str, object]:
    contenido = await request.body()
    if not contenido:
        raise HTTPException(status_code=400, detail="Selecciona data/ventas.csv.")
    if not CSV_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"No se encontró el dataset local: {CSV_PATH}")

    huella_subida = hashlib.sha256(contenido).digest()
    huella_canonica = hashlib.sha256(CSV_PATH.read_bytes()).digest()
    if not hmac.compare_digest(huella_subida, huella_canonica):
        raise HTTPException(
            status_code=422,
            detail="Solo se acepta el archivo canónico data/ventas.csv de ZENIT.",
        )

    return _cargar_csv_canonico()


@app.post("/api/zenit/cargar-local")
def cargar_dataset_local() -> Dict[str, object]:
    """Carga el CSV incluido en el paquete de escritorio de ZENIT."""
    return _cargar_csv_canonico()


@app.get("/api/zenit/estado")
def obtener_estado() -> Dict[str, object]:
    return _obtener_estado()


@app.post("/api/zenit/predecir")
def predecir(solicitud: SolicitudPrediccion) -> Dict[str, object]:
    estado = _obtener_estado()
    if not estado["datos_cargados"]:
        raise HTTPException(status_code=409, detail="Carga data/ventas.csv antes de predecir.")

    fecha_corte = solicitud.fecha_corte.isoformat()
    try:
        predicciones, tiempo_ms = _predecir_lote(fecha_corte)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (FileNotFoundError, RuntimeError) as exc:
        logger.exception("Falló la inferencia local del TFT.")
        raise HTTPException(status_code=503, detail=f"No se pudo ejecutar el TFT: {exc}") from exc

    cuadrantes_esperados = {
        p["producto"]: p["cuadrante_kraljic"] for p in estado["productos"]
    }
    productos_obtenidos = {p["producto"] for p in predicciones}
    cuadrantes_coinciden = all(
        p["cuadrante_kraljic"] == cuadrantes_esperados.get(p["producto"])
        for p in predicciones
    )
    if len(predicciones) != 50 or productos_obtenidos != set(cuadrantes_esperados) or not cuadrantes_coinciden:
        raise HTTPException(
            status_code=503,
            detail="El TFT no devolvió una predicción coherente para los 50 productos.",
        )

    db.guardar_predicciones(predicciones, tiempo_ms, fecha_corte, DB_PATH)
    logger.info(
        "Inferencia TFT para 50 productos: %.2f ms (corte %s).",
        tiempo_ms,
        fecha_corte,
    )
    return _obtener_estado()


@app.get("/api/zenit/ordenes")
def obtener_ordenes() -> List[Dict[str, object]]:
    return db.obtener_ordenes(DB_PATH)


@app.post("/api/zenit/ordenes/{orden_id}/aprobar")
def aprobar_orden(orden_id: int) -> Dict[str, object]:
    if not db.aprobar_orden(orden_id, DB_PATH):
        raise HTTPException(
            status_code=409,
            detail="La orden no existe o ya no está pendiente de aprobación.",
        )
    ordenes = db.obtener_ordenes(DB_PATH)
    return next(orden for orden in ordenes if orden["id"] == orden_id)


@app.get("/api/zenit/agente/estado")
def estado_agente(modelo: Optional[str] = None) -> Dict[str, object]:
    return obtener_estado_ollama(modelo_solicitado=modelo)


@app.post("/api/zenit/agente/chat")
def chat_agente(solicitud: SolicitudChatAgente) -> Dict[str, object]:
    try:
        return ejecutar_chat_agente(
            mensaje=solicitud.mensaje,
            historial=[{"role": t.role, "content": t.content} for t in solicitud.historial],
            db_path=DB_PATH,
            obtener_estado_fn=_obtener_estado,
            ejecutar_prediccion_fn=_predecir_lote,
            modelo_solicitado=solicitud.modelo,
            fecha_corte_default=solicitud.fecha_corte.isoformat(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
