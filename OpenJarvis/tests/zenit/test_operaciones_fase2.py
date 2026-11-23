"""Pruebas automatizadas de la Fase 2: Recepción física, Lotes, FEFO Caducidades y Cadena de Frío."""
import pytest
from fastapi.testclient import TestClient

import db
from zenit_api import app

cliente = TestClient(app)


def test_recepcion_medicamento_ambiente():
    payload = {
        "producto": "Paracetamol 500mg",
        "lote_id": "LOTE-PARAC-2026-01",
        "cantidad_recibida": 200,
        "fecha_caducidad": "2027-10-15",
        "ubicacion": "Anaquel B2",
        "recibido_por": "almacenista_test",
    }
    resp = cliente.post("/api/zenit/recepciones", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["producto"] == "Paracetamol 500mg"
    assert data["lote_id"] == "LOTE-PARAC-2026-01"
    assert data["estado_lote"] == "activo"
    assert data["excursion_termica"] is False


def test_recepcion_refrigerado_con_excursion_termica():
    # Insulina glargina requiere refrigeración (2°C - 8°C).
    # Si llega a 15°C, debe entrar automáticamente a estado 'cuarentena' y marcar excursión.
    payload = {
        "producto": "Insulina glargina",
        "lote_id": "LOTE-INS-EXCURSION-01",
        "cantidad_recibida": 50,
        "fecha_caducidad": "2027-06-30",
        "temperatura_recepcion": 15.4,
        "ubicacion": "Refrigerador 1",
    }
    resp = cliente.post("/api/zenit/recepciones", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["estado_lote"] == "cuarentena"
    assert data["excursion_termica"] is True


def test_recepcion_refrigerado_optimo():
    # Temperatura dentro del rango seguro (4.5°C)
    payload = {
        "producto": "Insulina glargina",
        "lote_id": "LOTE-INS-OPTIMO-02",
        "cantidad_recibida": 100,
        "fecha_caducidad": "2027-08-30",
        "temperatura_recepcion": 4.5,
        "ubicacion": "Refrigerador 1",
    }
    resp = cliente.post("/api/zenit/recepciones", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["estado_lote"] == "activo"
    assert data["excursion_termica"] is False


def test_alertas_caducidad_fefo():
    # Insertar un lote próximo a vencer (a 20 días)
    payload = {
        "producto": "Omeprazol 20mg",
        "lote_id": "LOTE-OMEP-PROXIMO",
        "cantidad_recibida": 40,
        "fecha_caducidad": "2026-11-30",
        "ubicacion": "Anaquel C1",
    }
    cliente.post("/api/zenit/recepciones", json=payload)

    resp = cliente.get("/api/zenit/caducidades?dias=60&fecha_referencia=2026-11-01")
    assert resp.status_code == 200
    alertas = resp.json()
    assert len(alertas) > 0
    # Verificar ordenamiento FEFO (los más cercanos a vencer van primero)
    assert any(a["lote_id"] == "LOTE-OMEP-PROXIMO" for a in alertas)
    assert alertas[0]["dias_restantes"] <= alertas[-1]["dias_restantes"]


def test_monitoreo_lecturas_frio():
    # Registro lectura normal (5.0°C)
    resp1 = cliente.post("/api/zenit/frio/lecturas", json={
        "equipo_id": "Refrigerador_Principal",
        "temperatura": 5.0,
        "registrado_por": "sensor_iot",
    })
    assert resp1.status_code == 200
    assert resp1.json()["en_rango"] == 1

    # Registro lectura con excursión térmica (9.5°C)
    resp2 = cliente.post("/api/zenit/frio/lecturas", json={
        "equipo_id": "Refrigerador_Principal",
        "temperatura": 9.5,
        "registrado_por": "sensor_iot",
    })
    assert resp2.status_code == 200
    assert resp2.json()["en_rango"] == 0

    # Consultar historial
    resp_hist = cliente.get("/api/zenit/frio/lecturas?equipo_id=Refrigerador_Principal&limite=5")
    assert resp_hist.status_code == 200
    lecturas = resp_hist.json()
    assert len(lecturas) >= 2
