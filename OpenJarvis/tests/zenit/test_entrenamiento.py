"""Regresiones de separación temporal, objetivo semanal y trazabilidad."""
import json

import numpy as np
import pytest
import torch

import db
from modelo.datos import (
    CSV_PATH, FIN_AJUSTE, DIAS_ENTRENAMIENTO, CrossEntropySemanal,
    crear_particiones_temporales, preparar_datos,
)
from modelo.entrenamiento import activar_modelo
from modelo.predecir import resumir_metricas


def test_etiquetas_y_normalizadores_no_ven_validacion_ni_prueba():
    df = preparar_datos(CSV_PATH)
    ajuste, validacion, peso, positivos, negativos = crear_particiones_temporales(df)
    assert ajuste.decoded_index.time_idx_last.max() < FIN_AJUSTE
    assert validacion.decoded_index.time_idx_first_prediction.min() >= FIN_AJUSTE
    assert validacion.decoded_index.time_idx_last.max() < DIAS_ENTRENAMIENTO
    assert positivos > 0 and negativos > 0 and peso == pytest.approx(negativos / positivos)
    alterado = df.copy()
    alterado.loc[alterado.time_idx >= FIN_AJUSTE, "existencia"] = 999999.
    otro, _, _, _, _ = crear_particiones_temporales(alterado)
    for nombre, escalador in ajuste.get_parameters()["scalers"].items():
        np.testing.assert_equal(escalador.mean_, otro.get_parameters()["scalers"][nombre].mean_)


def test_perdida_aprende_evento_semanal_sin_contar_duracion_del_quiebre():
    perdida = CrossEntropySemanal(peso_positivo=3)
    logits = torch.tensor([[[0., 1.]] * 7], requires_grad=True)
    inicio = torch.tensor([[0, 0, 0, 0, 0, 0, 1]])
    persistente = torch.ones((1, 7), dtype=torch.long)
    assert torch.equal(perdida.loss(logits, inicio), perdida.loss(logits, persistente))
    perdida.loss(logits, inicio).mean().backward()
    assert torch.isfinite(logits.grad).all()


def test_metricas_castigan_omitir_todos_los_quiebres_y_calibracion_incluye_uno():
    reporte = resumir_metricas([0, 1, 1], [0., 0., 0.])
    assert reporte["f1"] == 0 and reporte["fn"] == 2
    perfecto = resumir_metricas([0, 1], [0., 1.])
    assert perfecto["f1"] == 1 and perfecto["brier"] == 0
    assert sum(b["casos"] for b in perfecto["calibracion"]) == 2


def test_historial_sobrevive_al_reemplazo_de_la_vista_actual(tmp_path):
    ruta = tmp_path / "historial.db"
    for fecha, riesgo in [("2026-10-20", .6), ("2026-10-21", .7)]:
        db.guardar_predicciones([{"producto": "A", "cuadrante_kraljic": "Estratégico", "probabilidad": riesgo,
            "modelo_version": "v2", "dataset_sha256": "huella", "objetivo": "evento_semanal_v1"}], 20., fecha, ruta)
    conn = db.get_connection(ruta)
    assert conn.execute("SELECT COUNT(*) FROM predicciones").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM predicciones_historico").fetchone()[0] == 2
    conn.close()
    db.guardar_evaluacion({"f1": .5}, ruta)
    assert db.obtener_evaluacion(ruta)["f1"] == .5


@pytest.mark.parametrize("estado", ["descartada", "pospuesta", "emitida", "recibida", "recibida_parcial", "obsoleta"])
def test_repetir_corte_no_revierte_una_decision_de_orden(tmp_path, estado):
    ruta = tmp_path / "ordenes.db"
    predicciones = [{"producto": "A", "cuadrante_kraljic": "Estratégico", "probabilidad": .9}]
    db.guardar_predicciones(predicciones, 20., "2026-10-22", ruta)
    conn = db.get_connection(ruta)
    with conn:
        conn.execute("UPDATE ordenes SET estado = ?", (estado,))
    conn.close()
    db.guardar_predicciones(predicciones, 20., "2026-10-22", ruta)
    assert len(db.obtener_ordenes(ruta)) == 1
    assert db.obtener_ordenes(ruta)[0]["estado"] == estado


def test_no_activa_candidata_rechazada_ni_pierde_modelo_anterior(tmp_path):
    candidata, activo = tmp_path / "mejor.ckpt", tmp_path / "activo.ckpt"
    candidata.write_bytes(b"nuevo")
    activo.write_bytes(b"anterior")
    reporte = {"apto_validacion": False, "ckpt_path": str(candidata)}
    (tmp_path / "entrenamiento.json").write_text(json.dumps(reporte))
    with pytest.raises(ValueError):
        activar_modelo(candidata, activo)
    assert activo.read_bytes() == b"anterior"


def test_activacion_conserva_respaldo_y_valida_huellas(tmp_path):
    import hashlib
    candidata, activo, datos = tmp_path / "mejor.ckpt", tmp_path / "activo.ckpt", tmp_path / "ventas.csv"
    candidata.write_bytes(b"nuevo")
    activo.write_bytes(b"anterior")
    datos.write_bytes(b"historial")
    reporte = {"apto_validacion": True, "ckpt_path": str(candidata), "csv_path": str(datos),
        "validacion": {"f1": .8, "positivos_reales": 10},
        "dataset_sha256": hashlib.sha256(datos.read_bytes()).hexdigest(),
        "checkpoint_sha256": hashlib.sha256(candidata.read_bytes()).hexdigest()}
    (tmp_path / "entrenamiento.json").write_text(json.dumps(reporte))
    activar_modelo(candidata, activo)
    assert activo.read_bytes() == b"nuevo"
    assert next((tmp_path / "versiones").glob("respaldo-*/activo.ckpt")).read_bytes() == b"anterior"
    datos.write_bytes(b"cambiado")
    with pytest.raises(ValueError, match="dataset"):
        activar_modelo(candidata, activo)


def test_api_guarda_evaluacion_sin_entrenar(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import zenit_api
    from modelo import predecir
    monkeypatch.setattr(zenit_api, "DB_PATH", tmp_path / "api.db")
    monkeypatch.setattr(predecir, "cargar_modelo", lambda: None)
    monkeypatch.setattr(predecir, "evaluar_ultimos_27_dias", lambda: {"f1": .5})
    monkeypatch.setattr(predecir, "_METADATA", {"modelo_version": "v2"})
    cliente = TestClient(zenit_api.app)
    assert cliente.get("/api/zenit/evaluacion").json() is None
    assert cliente.post("/api/zenit/evaluar").json()["modelo_version"] == "v2"
    assert cliente.get("/api/zenit/evaluacion").json()["f1"] == .5


def test_entrenamiento_real_recupera_checkpoint_y_no_sobrescribe_activo(tmp_path):
    from modelo.entrenar_tft import entrenar_tft
    from modelo.predecir import predecir_lote
    activo = tmp_path / "activo.ckpt"
    activo.write_bytes(b"modelo anterior")
    reporte = entrenar_tft(ckpt_path=activo, max_epochs=1)
    assert activo.read_bytes() == b"modelo anterior"
    assert reporte["ventanas_ajuste"] == 750
    assert reporte["ventanas_validacion"] == 400
    assert reporte["criterios_activacion"]["positivos_validacion_minimos"] == 10
    resultados, _ = predecir_lote("2026-10-22", csv_path=CSV_PATH, ckpt_path=reporte["ckpt_path"])
    assert len(resultados) == 50
    assert all(0 <= p["probabilidad"] <= 1 for p in resultados)
    assert all(p["objetivo"] == "evento_semanal_v1" for p in resultados)
    assert all(p["modelo_version"] == reporte["modelo_version"] for p in resultados)
