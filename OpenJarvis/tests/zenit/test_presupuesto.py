"""Pruebas automatizadas del motor de presupuestos y cotizaciones de ZENIT."""
from pathlib import Path

import pytest

import db
from presupuesto import calcular_presupuesto, obtener_demanda_diaria_sin_quiebre


def test_catalogo_precios_cargado_en_db():
    conn = db.get_connection(db.DB_PATH)
    total_precios = conn.execute("SELECT COUNT(*) FROM catalogo_precios").fetchone()[0]
    conn.close()
    assert total_precios == 50, f"Se esperaban 50 productos con precio en catalogo_precios, hay {total_precios}"


def test_demanda_diaria_sin_sesgo_quiebre():
    demanda = obtener_demanda_diaria_sin_quiebre("Insulina glargina", "2026-10-22", db_path=db.DB_PATH)
    assert isinstance(demanda, float)
    assert demanda >= 0.0


def test_calculo_presupuesto_global():
    res = calcular_presupuesto("2026-10-22", db_path=db.DB_PATH)
    assert "resumen" in res
    assert "financiadas" in res
    assert "no_financiadas" in res

    resumen = res["resumen"]
    assert resumen["fecha_corte"] == "2026-10-22"
    assert resumen["total_alertas"] >= 0
    assert resumen["subtotal_mxn"] >= 0.0
    assert resumen["total_mxn"] >= 0.0
    assert resumen["costo_total_requerido_mxn"] >= 0.0


def test_calculo_presupuesto_con_techo_semanal():
    # Con un techo muy bajo (ej. 100 pesos), las líneas deben ir a no_financiadas y generar faltante
    res_bajo = calcular_presupuesto("2026-10-22", techo_mxn=100.0, db_path=db.DB_PATH)
    resumen_bajo = res_bajo["resumen"]
    assert resumen_bajo["techo_presupuestal_mxn"] == 100.0
    if resumen_bajo["total_alertas"] > 0:
        assert resumen_bajo["lineas_no_financiadas"] > 0
        assert resumen_bajo["faltante_mxn"] > 0.0

    # Con un techo holgado (ej. 100,000 pesos), todo lo que esté en alerta debe quedar financiado
    res_alto = calcular_presupuesto("2026-10-22", techo_mxn=100000.0, db_path=db.DB_PATH)
    resumen_alto = res_alto["resumen"]
    assert resumen_alto["lineas_no_financiadas"] == 0
    assert resumen_alto["faltante_mxn"] == 0.0


def test_endpoint_presupuesto_en_api():
    from fastapi.testclient import TestClient
    from zenit_api import app

    cliente = TestClient(app)
    resp = cliente.get("/api/zenit/presupuesto?fecha_corte=2026-10-22&techo=25000.0")
    assert resp.status_code == 200
    data = resp.json()
    assert "resumen" in data
    assert "financiadas" in data
    assert "no_financiadas" in data
    assert data["resumen"]["techo_presupuestal_mxn"] == 25000.0
