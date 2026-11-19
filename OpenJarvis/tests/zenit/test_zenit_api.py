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
    estado = cliente_api.get("/api/zenit/estado").json()
    assert estado["datos_cargados"] is False
    assert estado["fecha_existencia"] is None


def test_estado_expone_existencias_del_ultimo_dia_registrado(cliente_api):
    carga = cliente_api.post("/api/zenit/cargar-local")
    assert carga.status_code == 200

    estado = cliente_api.get("/api/zenit/estado").json()
    with db.CSV_PATH.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    fecha_existencia = max(fila["fecha"] for fila in filas)
    existencias_esperadas = {
        fila["producto"]: int(fila["existencia"])
        for fila in filas
        if fila["fecha"] == fecha_existencia
    }

    assert estado["fecha_existencia"] == fecha_existencia
    assert len(estado["productos"]) == 50
    assert {
        producto["producto"]: producto["existencia"]
        for producto in estado["productos"]
    } == existencias_esperadas


def test_tft_real_alimenta_kpis_de_existencias_alertas_y_sugerencias(cliente_api):
    carga = cliente_api.post("/api/zenit/cargar-local")
    assert carga.status_code == 200

    respuesta = cliente_api.post(
        "/api/zenit/predecir",
        json={"fecha_corte": "2026-10-22"},
    )

    assert respuesta.status_code == 200
    estado = respuesta.json()
    productos = estado["productos"]
    assert len(productos) == 50
    assert estado["fecha_existencia"]
    assert estado["inferencia"]["fecha_corte"] == "2026-10-22"
    assert estado["inferencia"]["tiempo_inferencia_ms"] > 0
    assert all(
        isinstance(producto["probabilidad"], (int, float))
        and 0 <= producto["probabilidad"] <= 1
        and producto["en_desabasto"] == (producto["probabilidad"] >= 0.50)
        for producto in productos
    )

    with db.CSV_PATH.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    fecha_existencia = max(fila["fecha"] for fila in filas)
    existencias_esperadas = {
        fila["producto"]: int(fila["existencia"])
        for fila in filas
        if fila["fecha"] == fecha_existencia
    }
    existencias = [producto["existencia"] for producto in productos]
    alertas = sum(producto["en_desabasto"] for producto in productos)
    pendientes = sum(
        producto["orden"] is not None and producto["orden"]["estado"] == "pendiente"
        for producto in productos
    )

    assert estado["fecha_existencia"] == fecha_existencia
    assert sum(existencias) == sum(existencias_esperadas.values())
    assert sum(existencia == 0 for existencia in existencias) == sum(
        existencia == 0 for existencia in existencias_esperadas.values()
    )
    assert pendientes == alertas


def test_carga_el_dataset_local_incluido_en_el_escritorio(cliente_api):
    respuesta = cliente_api.post("/api/zenit/cargar-local")

    assert respuesta.status_code == 200
    assert respuesta.json()["filas"] == 4500
    assert respuesta.json()["productos"] == 50
    assert respuesta.json()["fechas"] == 90


def test_cors_permite_solo_el_origen_webview_local(cliente_api):
    respuesta = cliente_api.options(
        "/api/zenit/cargar-local",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://tauri.localhost"


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
