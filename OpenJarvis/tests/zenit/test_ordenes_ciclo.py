"""Pruebas del ciclo de vida de órdenes, transiciones de estado, proveedores y bitácora."""
import pytest
from fastapi.testclient import TestClient

import db
from zenit_api import app

cliente = TestClient(app)


def test_catalogo_proveedores():
    resp = cliente.get("/api/zenit/proveedores")
    assert resp.status_code == 200
    proveedores = resp.json()
    assert len(proveedores) >= 3
    assert any(p["id"] == "PROV-FARMA-NAL-01" for p in proveedores)


def test_ciclo_completo_orden():
    # 1. Insertar una orden pendiente de prueba
    conn = db.get_connection(db.DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ordenes (producto, cuadrante_kraljic, cantidad_sugerida, probabilidad_desabasto, fecha_corte, estado)
        VALUES ('Insulina glargina', 'Estratégico', 50, 0.95, '2026-10-22', 'pendiente');
    """)
    orden_id = cur.lastrowid
    conn.commit()
    conn.close()

    # 2. Aprobar la orden con cantidad ajustada
    resp_aprob = cliente.post(f"/api/zenit/ordenes/{orden_id}/aprobar", json={"cantidad": 60, "usuario": "farmaceutico_jefe"})
    assert resp_aprob.status_code == 200
    data_aprob = resp_aprob.json()
    assert data_aprob["estado"] == "aprobada"
    assert data_aprob["cantidad_aprobada"] == 60

    # 3. Intentar volver a aprobar debe dar 409
    resp_reaprob = cliente.post(f"/api/zenit/ordenes/{orden_id}/aprobar", json={})
    assert resp_reaprob.status_code == 409

    # 4. Emitir la orden aprobada
    resp_emit = cliente.post(f"/api/zenit/ordenes/{orden_id}/emitir", json={"proveedor_id": "PROV-FARMA-NAL-01"})
    assert resp_emit.status_code == 200
    data_emit = resp_emit.json()
    assert data_emit["estado"] == "emitida"
    assert "ORD-ZENIT-" in str(data_emit["folio_emision"])

    # 5. Recepción física de la orden emitida
    resp_recib = cliente.post(f"/api/zenit/ordenes/{orden_id}/recibir", json={"cantidad_recibida": 60})
    assert resp_recib.status_code == 200
    data_recib = resp_recib.json()
    assert data_recib["estado"] == "recibida"


def test_descartar_y_posponer_orden():
    conn = db.get_connection(db.DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ordenes (producto, cuadrante_kraljic, cantidad_sugerida, probabilidad_desabasto, fecha_corte, estado)
        VALUES ('Paracetamol 500mg', 'Apalancamiento', 100, 0.80, '2026-10-22', 'pendiente');
    """)
    orden_id_1 = cur.lastrowid

    cur.execute("""
        INSERT INTO ordenes (producto, cuadrante_kraljic, cantidad_sugerida, probabilidad_desabasto, fecha_corte, estado)
        VALUES ('Ibuprofeno 400mg', 'Apalancamiento', 80, 0.75, '2026-10-22', 'pendiente');
    """)
    orden_id_2 = cur.lastrowid
    conn.commit()
    conn.close()

    # Descartar orden 1 con motivo
    resp_desc = cliente.post(f"/api/zenit/ordenes/{orden_id_1}/descartar", json={"motivo": "Stock suficiente en bodega alterna"})
    assert resp_desc.status_code == 200
    assert resp_desc.json()["estado"] == "descartada"
    assert resp_desc.json()["motivo_descarte"] == "Stock suficiente en bodega alterna"

    # Posponer orden 2 con fecha
    resp_posp = cliente.post(f"/api/zenit/ordenes/{orden_id_2}/posponer", json={"fecha_hasta": "2026-11-01"})
    assert resp_posp.status_code == 200
    assert resp_posp.json()["estado"] == "pospuesta"
    assert resp_posp.json()["pospuesta_hasta"] == "2026-11-01"


def test_bitacora_inmutable():
    conn = db.get_connection(db.DB_PATH)
    eventos = conn.execute("SELECT * FROM bitacora ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    assert len(eventos) > 0
    tipos_evento = [e["evento"] for e in eventos]
    assert any("ORDEN_" in tipo for tipo in tipos_evento)
