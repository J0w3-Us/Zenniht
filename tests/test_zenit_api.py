import csv

import pytest
from fastapi.testclient import TestClient

import db
import zenit_api


@pytest.fixture
def cliente_api(tmp_path, monkeypatch):
    monkeypatch.setattr(zenit_api, "DB_PATH", tmp_path / "zenith.db")
    return TestClient(zenit_api.app)


def test_carga_requiere_el_csv_canonico(cliente_api):
    respuesta = cliente_api.post(
        "/api/zenit/cargar",
        content=b"producto,fecha\nmedicamento,2026-10-22\n",
    )

    assert respuesta.status_code == 422
    assert "archivo canónico" in respuesta.json()["detail"]
    assert cliente_api.get("/api/zenit/estado").json()["datos_cargados"] is False


def test_predict_y_aprobar_ordenes_sin_inventar_cantidades(cliente_api, monkeypatch):
    carga = cliente_api.post(
        "/api/zenit/cargar",
        content=db.CSV_PATH.read_bytes(),
        headers={"Content-Type": "text/csv"},
    )
    assert carga.status_code == 200

    with db.CSV_PATH.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    productos = sorted({fila["producto"] for fila in filas})
    cuadrantes = {fila["producto"]: fila["cuadrante_kraljic"] for fila in filas}

    def prediccion_falsa(fecha_corte):
        return [
            {
                "producto": producto,
                "cuadrante_kraljic": cuadrantes[producto],
                "probabilidad": 0.75 if producto == productos[0] else 0.10,
                "en_desabasto": int(producto == productos[0]),
                "fecha_corte": fecha_corte,
            }
            for producto in productos
        ], 123.4

    monkeypatch.setattr(zenit_api, "_predecir_lote", prediccion_falsa)
    respuesta = cliente_api.post(
        "/api/zenit/predecir",
        json={"fecha_corte": "2026-10-22"},
    )

    assert respuesta.status_code == 200
    estado = respuesta.json()
    assert len(estado["productos"]) == 50
    assert estado["inferencia"]["tiempo_inferencia_ms"] == 123.4
    alerta = next(p for p in estado["productos"] if p["producto"] == productos[0])
    assert alerta["orden"]["estado"] == "pendiente"
    assert alerta["orden"]["cantidad_sugerida"] is None

    aprobacion = cliente_api.post(
        f"/api/zenit/ordenes/{alerta['orden']['id']}/aprobar",
    )

    assert aprobacion.status_code == 200
    assert aprobacion.json()["estado"] == "aprobada"
