"""Motor de presupuestos, cotizaciones y cálculo de necesidades para ZENIT.

Lee directamente la tabla `catalogo_precios` ya existente en `zenith.db`
(con `precio_compra_unitario` y `lote_minimo_compra`).
Realiza cálculos monetarios en centavos enteros con IVA (medicamentos tasa 0%, insumos tasa 16%),
aplica la fórmula empírica sin sesgo de quiebre y priorización Kraljic con techo presupuestal.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import db

COBERTURA_OBJETIVO_DIAS = 10
DIAS_VENTAS_HISTORICO = 14

JERARQUIA_KRALJIC = {
    "Estratégico": 1,
    "Cuello de botella": 2,
    "Apalancamiento": 3,
    "No crítico": 4,
}

INSUMOS_CON_IVA_16 = {
    "Gel antibacterial 500ml",
    "Alcohol etílico 70% 1L",
    "Gasas esterilizadas paquete",
    "Venda elástica 5cm",
    "Venda elástica 10cm",
    "Jeringa desechable 5ml c/10",
    "Cubrebocas tricapa c/50",
    "Termómetro digital",
}


def obtener_demanda_diaria_sin_quiebre(
    producto: str,
    fecha_corte: str,
    db_path: Optional[Path] = None,
    dias_historia: int = DIAS_VENTAS_HISTORICO,
) -> float:
    """Calcula el promedio diario de ventas considerando únicamente días con existencia > 0."""
    conn = db.get_connection(db_path)
    filas = conn.execute("""
        SELECT unidades_vendidas, existencia
        FROM ventas
        WHERE producto = ? AND fecha <= ?
        ORDER BY fecha DESC
        LIMIT ?
    """, (producto, fecha_corte, dias_historia)).fetchall()
    conn.close()

    if not filas:
        return 0.0

    dias_con_stock = [f["unidades_vendidas"] for f in filas if f["existencia"] > 0]
    if not dias_con_stock:
        return float(sum(f["unidades_vendidas"] for f in filas) / len(filas))

    return float(sum(dias_con_stock) / len(dias_con_stock))


def calcular_presupuesto(
    fecha_corte: Optional[str] = None,
    techo_mxn: Optional[float] = None,
    db_path: Optional[Path] = None,
    cobertura_dias: int = COBERTURA_OBJETIVO_DIAS,
) -> Dict[str, Any]:
    """Calcula el presupuesto y cotización de reabasto según predicciones y catálogo de precios."""
    db.init_db(db_path)
    conn = db.get_connection(db_path)

    # 1. Determinar fecha de corte
    if not fecha_corte:
        max_fecha = conn.execute("SELECT MAX(fecha) FROM ventas").fetchone()[0]
        fecha_corte = str(max_fecha) if max_fecha else "2026-10-22"

    # 2. Obtener existencias actuales a la fecha de corte
    existencias_rows = conn.execute("""
        SELECT producto, existencia, cuadrante_kraljic
        FROM ventas
        WHERE fecha = ?
    """, (fecha_corte,)).fetchall()

    if not existencias_rows:
        max_fecha = conn.execute("SELECT MAX(fecha) FROM ventas").fetchone()[0]
        fecha_corte = str(max_fecha) if max_fecha else "2026-10-22"
        existencias_rows = conn.execute("""
            SELECT producto, existencia, cuadrante_kraljic
            FROM ventas
            WHERE fecha = ?
        """, (fecha_corte,)).fetchall()

    # 3. Obtener predicciones TFT vigentes
    predicciones = {
        p["producto"]: p for p in db.obtener_predicciones(db_path)
    }

    # 4. Obtener unidades en tránsito
    ordenes_activas = conn.execute("""
        SELECT producto, SUM(COALESCE(cantidad_sugerida, 0)) as transito
        FROM ordenes
        WHERE estado IN ('pendiente', 'aprobada', 'emitida')
        GROUP BY producto
    """).fetchall()
    transito_por_prod = {row["producto"]: int(row["transito"] or 0) for row in ordenes_activas}

    # 5. Obtener catálogo de precios existente
    precios_rows = conn.execute("SELECT * FROM catalogo_precios").fetchall()
    catalogo_precios = {p["producto"]: dict(p) for p in precios_rows}
    conn.close()

    lineas_candidatas: List[Dict[str, Any]] = []

    for fila in existencias_rows:
        producto = fila["producto"]
        cuadrante = fila["cuadrante_kraljic"]
        existencia = int(fila["existencia"])
        pred = predicciones.get(producto)
        probabilidad = float(pred["probabilidad"]) if pred else 0.0

        # Alerta: probabilidad TFT >= 50% o existencia en 0
        en_alerta = probabilidad >= 0.50 or existencia == 0
        if not en_alerta:
            continue

        demanda_diaria = obtener_demanda_diaria_sin_quiebre(producto, fecha_corte, db_path=db_path)
        transito = transito_por_prod.get(producto, 0)
        precio_info = catalogo_precios.get(producto)

        banderas = []
        if not precio_info:
            banderas.append("sin_precio")
            lote_minimo = 1
            precio_centavos = 0
            tasa_iva = 0.0
        else:
            lote_minimo = max(1, int(precio_info.get("lote_minimo_compra") or 1))
            precio_unitario_float = float(precio_info.get("precio_compra_unitario") or 0.0)
            precio_centavos = int(round(precio_unitario_float * 100))
            tasa_iva = 16.0 if producto in INSUMOS_CON_IVA_16 else 0.0

        # Fórmula empírica de reabasto
        necesidad = max(0.0, (demanda_diaria * cobertura_dias) - existencia - transito)
        if necesidad <= 0:
            cantidad_sugerida = lote_minimo
        else:
            cantidad_sugerida = int(math.ceil(necesidad / lote_minimo) * lote_minimo)

        # Cálculo en centavos
        subtotal_centavos = cantidad_sugerida * precio_centavos
        iva_centavos = int(round(subtotal_centavos * (tasa_iva / 100.0)))
        total_centavos = subtotal_centavos + iva_centavos

        cobertura_restante_dias = round(existencia / demanda_diaria, 1) if demanda_diaria > 0 else 0.0

        lineas_candidatas.append({
            "producto": producto,
            "cuadrante": cuadrante,
            "jerarquia_kraljic": JERARQUIA_KRALJIC.get(cuadrante, 99),
            "riesgo_tft": round(probabilidad, 4),
            "demanda_diaria": round(demanda_diaria, 2),
            "existencia": existencia,
            "transito": transito,
            "cobertura_restante_dias": cobertura_restante_dias,
            "cantidad_sugerida": cantidad_sugerida,
            "lote_minimo": lote_minimo,
            "precio_compra_centavos": precio_centavos,
            "precio_unitario_mxn": round(precio_centavos / 100.0, 2),
            "tasa_iva_pct": tasa_iva,
            "subtotal_centavos": subtotal_centavos,
            "iva_centavos": iva_centavos,
            "total_centavos": total_centavos,
            "subtotal_mxn": round(subtotal_centavos / 100.0, 2),
            "iva_mxn": round(iva_centavos / 100.0, 2),
            "total_mxn": round(total_centavos / 100.0, 2),
            "banderas": banderas,
        })

    # Ordenar por:
    # 1. Jerarquía Kraljic
    # 2. Mayor riesgo TFT
    # 3. Menor cobertura restante
    lineas_candidatas.sort(
        key=lambda x: (x["jerarquia_kraljic"], -x["riesgo_tft"], x["cobertura_restante_dias"])
    )

    techo_centavos = int(round(techo_mxn * 100)) if (techo_mxn is not None and techo_mxn > 0) else None

    financiadas: List[Dict[str, Any]] = []
    no_financiadas: List[Dict[str, Any]] = []

    saldo_centavos = techo_centavos
    subtotal_acum = 0
    iva_acum = 0
    total_acum = 0

    for linea in lineas_candidatas:
        costo_linea = linea["total_centavos"]
        if saldo_centavos is None:
            financiadas.append(linea)
            subtotal_acum += linea["subtotal_centavos"]
            iva_acum += linea["iva_centavos"]
            total_acum += costo_linea
        else:
            if costo_linea <= saldo_centavos:
                financiadas.append(linea)
                saldo_centavos -= costo_linea
                subtotal_acum += linea["subtotal_centavos"]
                iva_acum += linea["iva_centavos"]
                total_acum += costo_linea
            else:
                no_financiadas.append(linea)

    costo_total_requerido = sum(l["total_centavos"] for l in lineas_candidatas)
    faltante_centavos = max(0, costo_total_requerido - total_acum)

    resumen = {
        "fecha_corte": fecha_corte,
        "cobertura_objetivo_dias": cobertura_dias,
        "techo_presupuestal_mxn": techo_mxn,
        "subtotal_mxn": round(subtotal_acum / 100.0, 2),
        "iva_mxn": round(iva_acum / 100.0, 2),
        "total_mxn": round(total_acum / 100.0, 2),
        "costo_total_requerido_mxn": round(costo_total_requerido / 100.0, 2),
        "faltante_mxn": round(faltante_centavos / 100.0, 2),
        "total_alertas": len(lineas_candidatas),
        "lineas_financiadas": len(financiadas),
        "lineas_no_financiadas": len(no_financiadas),
    }

    return {
        "resumen": resumen,
        "financiadas": financiadas,
        "no_financiadas": no_financiadas,
    }
