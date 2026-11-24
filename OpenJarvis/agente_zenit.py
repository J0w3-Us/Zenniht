"""Agente local de ZENIT impulsado por Ollama con herramientas sobre SQLite y TFT.

Arquitectura y guardrails obligatorios:
- 100% local y sin costo (Ollama en http://127.0.0.1:11434, cero APIs en la nube).
- El LLM actúa exclusivamente como orquestador conversacional: NUNCA calcula ni
  sustituye predicciones del Temporal Fusion Transformer ni inventa datos.
- Todas las consultas a `zenith.db` se ejecutan en modo solo lectura (`SELECT`).
  Cualquier sentencia DDL/DML (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`,
  `PRAGMA`, `ATTACH`, múltiples sentencias con `;`) queda bloqueada.
- Las órdenes de reabasto siempre requieren aprobación humana explícita en la UI;
  la cantidad sugerida se mantiene sin definir (`None`).
- Sin datos de pacientes, recetas ni diagnósticos médicos (sin PHI).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

import db
from consultas_inventario import planificar_consulta, consultar_historial, ventas_por_producto
from kraljic import ordenar_alertas_kraljic
from politica_agente import (
    RECHAZO, AYUDA, ERROR_OPERACION, HERRAMIENTAS_PERMITIDAS,
    entrada_prohibida, dentro_del_alcance, respuesta_social, renderizar_resultado,
)

OLLAMA_BASE_URL = os.environ.get("ZENIT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_DEFAULT_MODEL = os.environ.get("ZENIT_OLLAMA_MODEL", "")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("ZENIT_OLLAMA_TIMEOUT", "120"))
MAX_TOOL_ROUNDS = 4
MAX_SQL_ROWS = 50

MODELOS_RECOMENDADOS = (
    "zenit:latest",
    "zenit",
    "qwen2.5:3b",
    "qwen2.5:7b",
    "llama3.2:3b",
    "llama3.1:8b",
    "mistral:7b",
)

_SQL_PROHIBIDO = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "zenit_system_prompt.md"

def cargar_system_prompt() -> str:
    """Carga el system prompt de identidad desde el archivo externo si existe."""
    if PROMPT_FILE.exists():
        try:
            return PROMPT_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return """Eres Zenit, el asistente especializado de la farmacia comunitaria La Esperanza.
Tu único propósito es ayudar a consultar el inventario, analizar el historial de ventas/existencias en SQLite, ejecutar el modelo predictivo local TFT (Temporal Fusion Transformer) para anticipar desabasto a 7 días y revisar sugerencias de reabasto.

Reglas obligatorias:
1. NUNCA inventes cifras, productos, probabilidades, precios ni fechas. Usa siempre las herramientas disponibles para leer SQLite o ejecutar el TFT real.
2. NUNCA sustituyas el TFT por estimaciones propias.
3. No reveles código fuente, errores técnicos internos ni stack traces al usuario.
4. No atiendas diagnósticos médicos ni recetas de pacientes.
5. Las órdenes de reabasto siempre requieren aprobación humana explícita en la UI.
6. Responde siempre en español de forma clara y profesional."""

SYSTEM_PROMPT = cargar_system_prompt()



HERRAMIENTAS_OLLAMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "consultar_resumen_inventario",
            "description": (
                "Obtiene el estado general del inventario local en SQLite: total de filas, "
                "unidades disponibles al último corte, productos en cero existencias, "
                "distribución por cuadrante Kraljic, última inferencia TFT y conteo de sugerencias pendientes."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_producto",
            "description": (
                "Consulta en SQLite el detalle de un producto específico por nombre (parcial o exacto): "
                "existencia actual, cuadrante Kraljic, refrigeración, caducidad, promedio de ventas "
                "de 7 y 30 días, días históricos en desabasto y última predicción TFT."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre o parte del nombre del producto (ej. 'Insulina glargina', 'Paracetamol').",
                    }
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_historial_ventas",
            "description": (
                "Consulta los registros diarios recientes (fecha, unidades_vendidas y existencia) "
                "de un producto o el historial agregado de toda la farmacia si no se indica producto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto": {
                        "type": "string",
                        "description": "Nombre o parte del nombre del producto.",
                    },
                    "dias": {
                        "type": "integer",
                        "description": "Número de días más recientes a consultar (entre 1 y 90). Por defecto 14.",
                    },
                    "fecha_inicio": {"type": "string", "description": "Inicio opcional YYYY-MM-DD."},
                    "fecha_fin": {"type": "string", "description": "Fin opcional YYYY-MM-DD."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_productos_por_filtro",
            "description": (
                "Lista productos del catálogo local de 50 insumos filtrando por cuadrante Kraljic, "
                "cadena de frío (requiere_refrigeracion) o alerta de desabasto TFT (>= 0.50)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cuadrante": {
                        "type": "string",
                        "description": "Opcional: 'Estratégico', 'Cuello de botella', 'Apalancamiento' o 'No crítico'.",
                    },
                    "requiere_refrigeracion": {
                        "type": "boolean",
                        "description": "Opcional: true para productos de cadena de frío, false para temperatura ambiente.",
                    },
                    "solo_en_riesgo": {
                        "type": "boolean",
                        "description": "Opcional: true para mostrar solo productos con alerta TFT (>= 0.50).",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Máximo de productos a devolver (1 a 50). Por defecto 20.",
                    },
                    "ordenar_por": {"type": "string", "enum": ["producto", "existencia_desc", "existencia_asc", "ventas_desc", "ventas_asc"],
                        "description": "Orden solicitado: mayores/menores existencias o ventas. No implica filtrar desabasto."},
                    "dias": {"type": "integer", "description": "Ventana para ordenar ventas, entre 1 y 90 días. Por defecto 90."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_prediccion_tft",
            "description": (
                "Ejecuta el modelo predictivo local TFT (Temporal Fusion Transformer en CPU) "
                "para los 50 productos en una fecha de corte YYYY-MM-DD (por defecto '2026-10-22'), "
                "guarda las predicciones y órdenes pendientes en SQLite y devuelve las alertas y el tiempo en ms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha_corte": {
                        "type": "string",
                        "description": "Fecha de corte en formato YYYY-MM-DD (por defecto '2026-10-22').",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_sugerencias_pendientes",
            "description": (
                "Consulta las órdenes de reabasto sugeridas en SQLite (pendientes y aprobadas). "
                "Recuerda que la cantidad sugerida no se inventa y la aprobación es exclusivamente humana."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_presupuesto_reabasto",
            "description": (
                "Calcula la cotización y presupuesto financiero de reabasto para los productos "
                "en alerta o quiebre de stock. Incluye costos en MXN (subtotal, IVA, total), "
                "cantidades ajustadas a lotes mínimos de compra, y permite simular un techo presupuestal "
                "priorizando por cuadrante Kraljic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "techo_mxn": {
                        "type": "number",
                        "description": "Opcional: límite o presupuesto disponible en pesos MXN (ej. 25000.0).",
                    },
                    "fecha_corte": {
                        "type": "string",
                        "description": "Opcional: fecha YYYY-MM-DD para el cálculo de existencias.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_sql_lectura",
            "description": (
                "Ejecuta una consulta SQL de SOLO LECTURA (únicamente SELECT sobre tablas "
                "`ventas`, `predicciones` u `ordenes` de SQLite) para responder preguntas analíticas "
                "específicas. Máximo 50 filas. Prohibido modificar o borrar datos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Sentencia SQL SELECT válida (sin punto y coma múltiple ni DDL/DML).",
                    }
                },
                "required": ["sql"],
            },
        },
    },
]


def validar_sql_solo_lectura(sql: str) -> str:
    """Valida que una consulta SQL sea estrictamente un SELECT de solo lectura."""
    limpio = sql.strip()
    if not limpio:
        raise ValueError("La consulta SQL está vacía.")
    if limpio.endswith(";"):
        limpio = limpio[:-1].strip()
    if ";" in limpio:
        raise ValueError("No se permiten múltiples sentencias SQL.")
    if "--" in limpio or "/*" in limpio or "*/" in limpio:
        raise ValueError("No se permiten comentarios dentro de la consulta SQL.")
    if not re.match(r"^(SELECT|WITH)\b", limpio, re.IGNORECASE):
        raise ValueError("Solo se permiten consultas de lectura que inicien con SELECT o WITH.")
    if _SQL_PROHIBIDO.search(limpio):
        raise ValueError("Guardrail de seguridad: la consulta contiene operaciones no permitidas.")
    return limpio


def ejecutar_sql_solo_lectura(sql: str, db_path: Path) -> Dict[str, Any]:
    """Ejecuta una consulta SELECT validada abriendo SQLite en modo solo lectura."""
    consulta = validar_sql_solo_lectura(sql)
    if not db_path.is_file():
        return {"error": f"La base de datos local no existe todavía: {db_path.name}"}

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(consulta)
        filas = [dict(fila) for fila in cursor.fetchmany(MAX_SQL_ROWS)]
        return {
            "filas_devueltas": len(filas),
            "limite_maximo": MAX_SQL_ROWS,
            "resultados": filas,
        }
    except sqlite3.Error as exc:
        return {"error": f"Error al ejecutar la consulta SELECT: {exc}"}
    finally:
        conn.close()


def _seleccionar_modelo_ollama(modelos: List[str], solicitado: Optional[str] = None) -> Optional[str]:
    """Elige el modelo Ollama a usar priorizando el solicitado o los recomendados."""
    if not modelos:
        return None
    if solicitado and solicitado in modelos:
        return solicitado
    if OLLAMA_DEFAULT_MODEL and OLLAMA_DEFAULT_MODEL in modelos:
        return OLLAMA_DEFAULT_MODEL
    for recomendado in MODELOS_RECOMENDADOS:
        if recomendado in modelos:
            return recomendado
    return modelos[0]


def obtener_estado_ollama(
    base_url: str = OLLAMA_BASE_URL,
    modelo_solicitado: Optional[str] = None,
) -> Dict[str, Any]:
    """Comprueba si Ollama local está activo y qué modelos tiene instalados."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        respuesta = httpx.get(url, timeout=1.5)
        respuesta.raise_for_status()
        payload = respuesta.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "ollama_disponible": False,
            "url": base_url,
            "modelos": [],
            "modelo_activo": None,
            "detalle": (
                "No se detectó Ollama en http://127.0.0.1:11434. "
                "Instala Ollama, ejecútalo localmente y descarga un modelo ligero "
                "(por ejemplo: `ollama pull qwen2.5:3b`)."
            ),
            "error_tecnico": str(exc),
        }

    modelos = [
        str(item["name"])
        for item in payload.get("models", [])
        if isinstance(item, dict) and item.get("name")
    ]
    modelo_activo = _seleccionar_modelo_ollama(modelos, modelo_solicitado)
    if not modelos:
        return {
            "ollama_disponible": True,
            "url": base_url,
            "modelos": [],
            "modelo_activo": None,
            "detalle": (
                "Ollama está activo, pero no tiene modelos descargados. "
                "Ejecuta en tu terminal: `ollama pull qwen2.5:3b`."
            ),
        }

    return {
        "ollama_disponible": True,
        "url": base_url,
        "modelos": modelos,
        "modelo_activo": modelo_activo,
        "detalle": f"Ollama local conectado ({modelo_activo}).",
    }


def _buscar_nombre_producto(conn: sqlite3.Connection, consulta: str) -> List[str]:
    from politica_agente import normalizar
    termino = normalizar(consulta.strip())
    if not termino:
        return []
    filas = conn.execute("SELECT DISTINCT producto FROM ventas ORDER BY producto").fetchall()
    nombres = [str(fila["producto"]) for fila in filas]
    exactos = [n for n in nombres if normalizar(n) == termino]
    if exactos:
        return exactos
    return [n for n in nombres if termino in normalizar(n)]


def ejecutar_herramienta_local(
    nombre: str,
    argumentos: Dict[str, Any],
    *,
    db_path: Path,
    obtener_estado_fn: Callable[[], Dict[str, Any]],
    ejecutar_prediccion_fn: Callable[[str], Tuple[List[Dict[str, object]], float]],
    fecha_corte_default: str = "2026-10-22",
) -> Tuple[Dict[str, Any], bool, str]:
    """Ejecuta una herramienta validada y devuelve (resultado, actualizo_estado, fuente)."""
    db.init_db(db_path)

    if nombre == "consultar_resumen_inventario":
        estado = obtener_estado_fn()
        productos = estado["productos"]
        por_cuadrante: Dict[str, int] = {}
        for item in productos:
            cuad = str(item["cuadrante_kraljic"])
            por_cuadrante[cuad] = por_cuadrante.get(cuad, 0) + 1
        alertas = [p for p in productos if p.get("en_desabasto") is True]
        sin_existencia = [p["producto"] for p in productos if p.get("existencia") == 0]
        pendientes = [o for o in estado["ordenes"] if o["estado"] == "pendiente"]
        con_prob = [
            p for p in productos
            if p.get("probabilidad") is not None
            and p.get("en_desabasto") is not True
            and float(p["probabilidad"]) > 0.0
        ]
        en_seguimiento = sorted(con_prob, key=lambda p: -float(p["probabilidad"]))[:3]
        menor_existencia = sorted(productos, key=lambda p: int(p["existencia"]))[:5]
        return (
            {
                "datos_cargados": estado["datos_cargados"],
                "filas": estado["filas"],
                "total_productos": len(productos),
                "fecha_existencia": estado["fecha_existencia"],
                "unidades_totales": sum(int(p["existencia"]) for p in productos),
                "productos_sin_existencia": sin_existencia,
                "distribucion_kraljic": por_cuadrante,
                "inferencia_tft": estado["inferencia"],
                "alertas_tft_activas": len(alertas),
                "productos_en_alerta_tft": [
                    {
                        "producto": p["producto"],
                        "cuadrante_kraljic": p["cuadrante_kraljic"],
                        "existencia": p["existencia"],
                        "probabilidad_tft_porcentaje": round(float(p["probabilidad"]) * 100.0, 1),
                    }
                    for p in alertas
                ],
                "otros_en_seguimiento_sin_alerta": [
                    {
                        "producto": p["producto"],
                        "cuadrante_kraljic": p["cuadrante_kraljic"],
                        "existencia": p["existencia"],
                        "probabilidad_tft_porcentaje": round(float(p["probabilidad"]) * 100.0, 1),
                    }
                    for p in en_seguimiento
                ],
                "productos_menor_existencia": [
                    {
                        "producto": p["producto"],
                        "cuadrante_kraljic": p["cuadrante_kraljic"],
                        "existencia": p["existencia"],
                    }
                    for p in menor_existencia
                ],
                "productos_mayor_existencia": [
                    {"producto": p["producto"], "existencia": p["existencia"]}
                    for p in sorted(productos, key=lambda p: (-int(p["existencia"]), p["producto"]))[:5]
                ],
                "ordenes_pendientes": len(pendientes),
            },
            False,
            "SQLITE LOCAL",
        )

    if nombre == "consultar_producto":
        termino = str(argumentos.get("nombre", "")).strip()
        if not termino:
            estado = obtener_estado_fn()
            productos = estado["productos"]
            alertas = [p for p in productos if p.get("en_desabasto") is True]
            menor = sorted(productos, key=lambda p: int(p["existencia"]))[:8]
            return (
                {
                    "nota": "No se indicó un producto específico; se muestran las alertas TFT activas y los productos con menor existencia.",
                    "productos_en_alerta_tft": [
                        {
                            "producto": p["producto"],
                            "cuadrante_kraljic": p["cuadrante_kraljic"],
                            "existencia": p["existencia"],
                            "probabilidad_tft": round(float(p["probabilidad"]), 4),
                        }
                        for p in alertas
                    ],
                    "productos_menor_existencia": [
                        {
                            "producto": p["producto"],
                            "cuadrante_kraljic": p["cuadrante_kraljic"],
                            "existencia": p["existencia"],
                            "probabilidad_tft": round(float(p["probabilidad"]), 4) if p.get("probabilidad") is not None else None,
                        }
                        for p in menor
                    ],
                },
                False,
                "SQLITE LOCAL",
            )
        conn = db.get_connection(db_path)
        try:
            coincidencias = _buscar_nombre_producto(conn, termino)
            if not coincidencias:
                return {"error": f"No se encontró ningún producto que coincida con '{termino}'."}, False, "SQLITE LOCAL"
            if len(coincidencias) > 1:
                return {
                    "coincidencias_multiples": coincidencias[:10],
                    "mensaje": "Especifica el nombre exacto del producto.",
                }, False, "SQLITE LOCAL"

            prod = coincidencias[0]
            ultimo = conn.execute(
                "SELECT * FROM ventas WHERE producto = ? ORDER BY fecha DESC LIMIT 1",
                (prod,),
            ).fetchone()
            stats_7 = conn.execute(
                "SELECT AVG(unidades_vendidas) AS prom_7d FROM ("
                "  SELECT unidades_vendidas FROM ventas WHERE producto = ? ORDER BY fecha DESC LIMIT 7"
                ")",
                (prod,),
            ).fetchone()
            stats_30 = conn.execute(
                "SELECT AVG(unidades_vendidas) AS prom_30d FROM ("
                "  SELECT unidades_vendidas FROM ventas WHERE producto = ? ORDER BY fecha DESC LIMIT 30"
                ")",
                (prod,),
            ).fetchone()
            quiebres = conn.execute(
                "SELECT COUNT(*) AS dias_quiebre FROM ventas WHERE producto = ? AND existencia = 0",
                (prod,),
            ).fetchone()
        finally:
            conn.close()

        estado = obtener_estado_fn()
        info_estado = next((p for p in estado["productos"] if p["producto"] == prod), None)
        return (
            {
                "producto": prod,
                "cuadrante_kraljic": ultimo["cuadrante_kraljic"] if ultimo else None,
                "requiere_refrigeracion": bool(ultimo["requiere_refrigeracion"]) if ultimo else None,
                "fecha_caducidad": ultimo["fecha_caducidad"] if ultimo else None,
                "fecha_ultimo_corte": ultimo["fecha"] if ultimo else None,
                "existencia_actual": int(ultimo["existencia"]) if ultimo else None,
                "ventas_promedio_7d": round(float(stats_7["prom_7d"] or 0.0), 2),
                "ventas_promedio_30d": round(float(stats_30["prom_30d"] or 0.0), 2),
                "dias_historicos_en_cero": int(quiebres["dias_quiebre"]) if quiebres else 0,
                "probabilidad_tft": info_estado["probabilidad"] if info_estado else None,
                "en_desabasto_tft": info_estado["en_desabasto"] if info_estado else None,
                "orden": info_estado["orden"] if info_estado else None,
            },
            False,
            "SQLITE LOCAL",
        )

    if nombre == "consultar_historial_ventas":
        resultado = consultar_historial(db_path, producto=str(argumentos.get("producto") or ""),
            dias=argumentos.get("dias", 14), fecha_inicio=argumentos.get("fecha_inicio"), fecha_fin=argumentos.get("fecha_fin"))
        return resultado, False, "SQLITE LOCAL"

    if nombre == "listar_productos_por_filtro":
        cuadrante = argumentos.get("cuadrante")
        requiere_ref = argumentos.get("requiere_refrigeracion")
        solo_riesgo = bool(argumentos.get("solo_en_riesgo", False))
        limite = max(1, min(50, int(argumentos.get("limite", 20) or 20)))
        ordenar_por = argumentos.get("ordenar_por", "producto")
        if ordenar_por not in {"producto", "existencia_desc", "existencia_asc", "ventas_desc", "ventas_asc"}:
            raise ValueError("Orden de productos no válido.")

        estado = obtener_estado_fn()
        conn = db.get_connection(db_path)
        try:
            ref_rows = conn.execute(
                "SELECT DISTINCT producto, requiere_refrigeracion, fecha_caducidad FROM ventas"
            ).fetchall()
            meta = {
                str(r["producto"]): {
                    "requiere_refrigeracion": bool(r["requiere_refrigeracion"]),
                    "fecha_caducidad": str(r["fecha_caducidad"]),
                }
                for r in ref_rows
            }
        finally:
            conn.close()

        filtrados = []
        for item in estado["productos"]:
            info = meta.get(str(item["producto"]), {})
            if cuadrante and str(item["cuadrante_kraljic"]).lower() != str(cuadrante).strip().lower():
                continue
            if requiere_ref is not None and info.get("requiere_refrigeracion") != bool(requiere_ref):
                continue
            if solo_riesgo and item.get("en_desabasto") is not True:
                continue
            filtrados.append({
                "producto": item["producto"],
                "cuadrante_kraljic": item["cuadrante_kraljic"],
                "existencia": item["existencia"],
                "requiere_refrigeracion": info.get("requiere_refrigeracion"),
                "probabilidad_tft": item["probabilidad"],
                "en_desabasto_tft": item["en_desabasto"],
            })

        fecha_inicio = None
        fecha_fin = estado.get("fecha_existencia")
        if ordenar_por.startswith("ventas_"):
            ventas, fecha_inicio, fecha_fin = ventas_por_producto(db_path, argumentos.get("dias", 90))
            for item in filtrados:
                item["unidades_vendidas"] = ventas.get(item["producto"], 0)
        campo = "unidades_vendidas" if ordenar_por.startswith("ventas_") else "existencia"
        if ordenar_por == "producto":
            filtrados.sort(key=lambda p: p["producto"])
        else:
            signo = -1 if ordenar_por.endswith("_desc") else 1
            filtrados.sort(key=lambda p: (signo * int(p.get(campo) or 0), p["producto"]))
        return {
            "total_coincidencias": len(filtrados),
            "productos": filtrados[:limite],
            "ordenar_por": ordenar_por, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
            "solo_en_riesgo": solo_riesgo,
        }, False, "SQLITE LOCAL"

    if nombre == "ejecutar_prediccion_tft":
        estado = obtener_estado_fn()
        if not estado["datos_cargados"]:
            return {"error": "Primero debe cargarse el dataset canónico data/ventas.csv."}, False, "TFT LOCAL"
        fecha_corte = str(argumentos.get("fecha_corte") or fecha_corte_default).strip()
        try:
            predicciones, tiempo_ms = ejecutar_prediccion_fn(fecha_corte)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            return {"error": f"No se pudo ejecutar el TFT local: {exc}"}, False, "TFT LOCAL"

        db.guardar_predicciones(predicciones, tiempo_ms, fecha_corte, db_path)
        ordenadas = ordenar_alertas_kraljic(predicciones)
        alertas = [p for p in ordenadas if float(p["probabilidad"]) >= 0.50]
        return (
            {
                "fecha_corte": fecha_corte,
                "tiempo_inferencia_ms": round(tiempo_ms, 2),
                "cumple_umbral_1000ms": tiempo_ms < 1000.0,
                "total_productos_evaluados": len(predicciones),
                "total_alertas": len(alertas),
                "alertas": [
                    {
                        "producto": p["producto"],
                        "cuadrante_kraljic": p["cuadrante_kraljic"],
                        "probabilidad": round(float(p["probabilidad"]), 4),
                    }
                    for p in alertas
                ],
                "top_riesgo": [
                    {
                        "producto": p["producto"],
                        "cuadrante_kraljic": p["cuadrante_kraljic"],
                        "probabilidad": round(float(p["probabilidad"]), 4),
                    }
                    for p in sorted(predicciones, key=lambda x: -float(x["probabilidad"]))[:5]
                ],
            },
            True,
            "TFT LOCAL",
        )

    if nombre == "consultar_sugerencias_pendientes":
        ordenes = db.obtener_ordenes(db_path)
        return (
            {
                "total_ordenes": len(ordenes),
                "pendientes": [o for o in ordenes if o["estado"] == "pendiente"],
                "aprobadas": [o for o in ordenes if o["estado"] == "aprobada"],
                "nota": "Toda aprobación es manual por el usuario y la cantidad queda por definir.",
            },
            False,
            "SQLITE LOCAL",
        )

    if nombre == "consultar_presupuesto_reabasto":
        from presupuesto import calcular_presupuesto
        techo = argumentos.get("techo_mxn")
        fecha = argumentos.get("fecha_corte")
        techo_val = float(techo) if techo is not None else None
        fecha_val = str(fecha) if fecha else None
        res_presupuesto = calcular_presupuesto(
            fecha_corte=fecha_val,
            techo_mxn=techo_val,
            db_path=db_path,
        )
        return res_presupuesto, False, "MOTOR PRESUPUESTAL ZENIT"

    if nombre == "consultar_sql_lectura":
        sql = str(argumentos.get("sql", ""))
        try:
            resultado = ejecutar_sql_solo_lectura(sql, db_path)
        except ValueError as exc:
            return {"error": str(exc)}, False, "SQLITE LOCAL"
        return resultado, False, "SQLITE LOCAL"

    return {"error": f"Herramienta desconocida: {nombre}"}, False, "SQLITE LOCAL"


def ejecutar_chat_agente(
    mensaje: str,
    historial: List[Dict[str, str]],
    *,
    db_path: Path,
    obtener_estado_fn: Callable[[], Dict[str, Any]],
    ejecutar_prediccion_fn: Callable[[str], Tuple[List[Dict[str, object]], float]],
    modelo_solicitado: Optional[str] = None,
    fecha_corte_default: str = "2026-10-22",
    base_url: str = OLLAMA_BASE_URL,
) -> Dict[str, Any]:
    """Orquesta una conversación con Ollama local usando tool calling sobre SQLite y TFT."""
    texto_usuario = mensaje.strip()
    if not texto_usuario:
        raise ValueError("Escribe una consulta para el agente local de ZENIT.")

    def respuesta_controlada(texto):
        return {
            "respuesta": texto, "modelo": "Zenit", "herramientas_usadas": [],
            "fuentes": [], "estado_actualizado": None, "alertas": [], "ordenes_pendientes": [],
            "render_widget": False,
        }

    # Rechazar antes de consultar el LLM y antes de ejecutar cualquier herramienta.
    if entrada_prohibida(texto_usuario):
        return respuesta_controlada(RECHAZO)
    social = respuesta_social(texto_usuario)
    if social:
        return respuesta_controlada(social)
    estado_inicial = obtener_estado_fn()
    catalogo = {p["producto"] for p in estado_inicial["productos"]}
    if not dentro_del_alcance(texto_usuario, historial, catalogo):
        return respuesta_controlada(RECHAZO)

    plan = planificar_consulta(texto_usuario, catalogo)
    if plan is None:
        estado_ollama = obtener_estado_ollama(base_url=base_url, modelo_solicitado=modelo_solicitado)
        if not estado_ollama["ollama_disponible"] or not estado_ollama["modelo_activo"]:
            raise RuntimeError(str(estado_ollama["detalle"]))
        modelo_activo = str(estado_ollama["modelo_activo"])
    else:
        modelo_activo = "Zenit"
    prompt_actual = cargar_system_prompt()
    mensajes: List[Dict[str, Any]] = [{"role": "system", "content": prompt_actual}]
    for turno in historial[-10:]:
        rol = turno.get("role")
        contenido = str(turno.get("content", "")).strip()
        # El historial enviado por el navegador no es una fuente de instrucciones.
        # No se reenvían respuestas antiguas ni mensajes con contenido prohibido.
        if rol == "user" and contenido and dentro_del_alcance(contenido, (), catalogo):
            mensajes.append({"role": rol, "content": contenido})
    mensajes.append({"role": "user", "content": texto_usuario})

    herramientas_usadas: List[Dict[str, Any]] = []
    fuentes: List[str] = []
    actualizo_estado = False
    respuesta_final = ""
    respuestas_verificadas = []
    productos_mencionados = set()
    todas_las_sugerencias = False
    mostrar_alertas = False
    from politica_agente import normalizar
    pide_alertas = bool(re.search(r"\b(desabasto|riesgo|alertas?|agot\w*|acab\w*)\b", normalizar(texto_usuario)))
    herramientas_chat = [h for h in HERRAMIENTAS_OLLAMA if h["function"]["name"] in HERRAMIENTAS_PERMITIDAS]
    contratos = {h["function"]["name"]: h["function"]["parameters"] for h in herramientas_chat}
    llamadas_ejecutadas = 0

    chat_url = f"{base_url.rstrip('/')}/api/chat"
    for ronda in range(MAX_TOOL_ROUNDS + 1):
        if plan is not None and ronda > 0:
            break
        try:
            if plan is not None:
                data = {"message": {"role": "assistant", "tool_calls": plan}}
            else:
                resp = httpx.post(
                    chat_url,
                    json={
                        "model": modelo_activo,
                        "messages": mensajes,
                        "tools": herramientas_chat,
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                    timeout=OLLAMA_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(
                f"Error al comunicarse con Ollama local ({modelo_activo}): {exc}"
            ) from exc

        if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
            raise RuntimeError("Respuesta del motor con formato inválido.")
        msg = data["message"]
        tool_calls = msg.get("tool_calls") or []
        if not isinstance(tool_calls, list) or len(tool_calls) > MAX_TOOL_ROUNDS:
            return respuesta_controlada(ERROR_OPERACION)
        mensajes.append({"role": "assistant", "content": "", "tool_calls": tool_calls})

        if not tool_calls:
            # Nunca publicar texto libre del LLM, aunque parezca una respuesta válida.
            break

        for llamada in tool_calls:
            if not isinstance(llamada, dict) or not isinstance(llamada.get("function"), dict):
                return respuesta_controlada(ERROR_OPERACION)
            fn = llamada.get("function") or {}
            nombre_tool = str(fn.get("name") or "")
            raw_args = fn.get("arguments") or {}
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except ValueError:
                    raw_args = {}

            if nombre_tool not in HERRAMIENTAS_PERMITIDAS or llamadas_ejecutadas >= MAX_TOOL_ROUNDS:
                return respuesta_controlada(RECHAZO)
            if not isinstance(raw_args, dict):
                return respuesta_controlada(ERROR_OPERACION)
            contrato = contratos[nombre_tool]
            propiedades = contrato.get("properties", {})
            if set(raw_args) - set(propiedades) or not set(contrato.get("required", [])).issubset(raw_args):
                return respuesta_controlada(ERROR_OPERACION)
            for clave, valor in raw_args.items():
                tipo = propiedades[clave].get("type")
                valido = ((tipo == "string" and isinstance(valor, str) and len(valor) <= 160)
                    or (tipo == "integer" and type(valor) is int and 1 <= valor <= (90 if clave == "dias" else 50))
                    or (tipo == "number" and type(valor) in (int, float) and 0 <= valor <= 1_000_000_000)
                    or (tipo == "boolean" and type(valor) is bool))
                if not valido or ("enum" in propiedades[clave] and valor not in propiedades[clave]["enum"]):
                    return respuesta_controlada(ERROR_OPERACION)
            for campo_fecha in ("fecha_corte", "fecha_inicio", "fecha_fin"):
                if not raw_args.get(campo_fecha):
                    continue
                from datetime import date
                try:
                    date.fromisoformat(raw_args[campo_fecha])
                except ValueError:
                    return respuesta_controlada(ERROR_OPERACION)
            llamadas_ejecutadas += 1

            try:
                resultado_tool, cambio_estado, fuente = ejecutar_herramienta_local(
                    nombre_tool, raw_args, db_path=db_path, obtener_estado_fn=obtener_estado_fn,
                    ejecutar_prediccion_fn=ejecutar_prediccion_fn, fecha_corte_default=fecha_corte_default,
                )
            except (ValueError, TypeError, KeyError, OSError, RuntimeError, sqlite3.Error):
                return respuesta_controlada(ERROR_OPERACION)
            respuesta_segura = renderizar_resultado(nombre_tool, resultado_tool, catalogo, incluir_alertas=pide_alertas)
            mostrar_alertas = mostrar_alertas or nombre_tool == "ejecutar_prediccion_tft" or (
                nombre_tool in {"consultar_resumen_inventario", "listar_productos_por_filtro"} and pide_alertas)
            if not resultado_tool.get("error"):
                if nombre_tool == "consultar_sugerencias_pendientes":
                    todas_las_sugerencias = True
                elif nombre_tool == "consultar_producto" and resultado_tool.get("producto"):
                    productos_mencionados.add(resultado_tool["producto"])
                for campo in ("productos_en_alerta_tft", "alertas", "productos", "financiadas", "no_financiadas"):
                    if campo == "productos" and not raw_args.get("solo_en_riesgo"):
                        continue
                    if campo == "productos_en_alerta_tft" and not pide_alertas:
                        continue
                    productos_mencionados.update(p["producto"] for p in resultado_tool.get(campo, []) if p.get("producto") in catalogo)
            if respuesta_segura not in respuestas_verificadas:
                respuestas_verificadas.append(respuesta_segura)
            if cambio_estado:
                actualizo_estado = True
            if fuente not in fuentes:
                fuentes.append(fuente)
            herramientas_usadas.append({
                "nombre": nombre_tool,
                "fuente": fuente,
            })
            mensajes.append({
                "role": "tool",
                "name": nombre_tool,
                "content": json.dumps({"resultado": respuesta_segura}, ensure_ascii=False),
            })

    respuesta_final = "\n\n".join(respuestas_verificadas) if respuestas_verificadas else AYUDA

    estado_actual = obtener_estado_fn()
    alertas_actuales = [
        p for p in estado_actual["productos"] if p.get("en_desabasto") is True
    ]
    # Sincronización atómica: si la respuesta fue un error o rechazo, nunca emitir widgets activos
    es_error = respuesta_final in (ERROR_OPERACION, RECHAZO) or not respuestas_verificadas
    ordenes_pendientes = (
        [o for o in estado_actual["ordenes"] if o.get("estado") == "pendiente"]
        if not es_error else []
    )

    return {
        "respuesta": respuesta_final,
        "modelo": modelo_activo,
        "herramientas_usadas": herramientas_usadas,
        "fuentes": fuentes,
        # También las consultas de lectura deben sincronizar la interfaz.
        "estado_actualizado": estado_actual,
        "alertas": alertas_actuales if not es_error else [],
        "mostrar_alertas": mostrar_alertas and not es_error,
        "ordenes_pendientes": ordenes_pendientes,
        "sugerencias_destacadas_ids": [
            o["id"] for o in ordenes_pendientes
            if todas_las_sugerencias or o["producto"] in productos_mencionados
        ] if not es_error else [],
        "render_widget": bool(not es_error and mostrar_alertas and len(alertas_actuales) > 0 and len(herramientas_usadas) > 0),
    }
