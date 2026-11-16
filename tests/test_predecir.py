from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from modelo import predecir


def test_cargar_modelo_falla_si_no_hay_checkpoint(monkeypatch, tmp_path):
    checkpoint = tmp_path / "modelo_inexistente.ckpt"
    monkeypatch.setattr(predecir, "CKPT_PATH", checkpoint)
    monkeypatch.setattr(predecir, "_MODELO_CACHE", None)

    with pytest.raises(FileNotFoundError, match="No se encontró el checkpoint TFT"):
        predecir.cargar_modelo()


def test_probabilidad_cercana_al_umbral_no_se_redondea_a_alerta(monkeypatch):
    fecha = pd.Timestamp("2026-10-22")
    filas = [
        {
            "producto": f"Producto {producto:02}",
            "fecha": fecha - pd.Timedelta(days=13 - dia),
            "time_idx": dia,
            "cuadrante_kraljic": "Estratégico",
        }
        for producto in range(50)
        for dia in range(14)
    ]
    df = pd.DataFrame(filas)
    probabilidad_semanal = 0.49996
    probabilidad_diaria = 1 - (1 - probabilidad_semanal) ** (1 / 7)
    logits_diarios = torch.tensor(
        [np.log1p(-probabilidad_diaria), np.log(probabilidad_diaria)],
        dtype=torch.float32,
    )
    logits = logits_diarios.repeat(50, 7, 1)

    class DatasetPrediccion:
        def to_dataloader(self, **kwargs):
            return object()

    class ModeloFalso:
        def predict(self, *args, **kwargs):
            return SimpleNamespace(
                output=SimpleNamespace(prediction=logits),
            )

    monkeypatch.setattr(
        predecir,
        "cargar_modelo",
        lambda: (ModeloFalso(), object(), df),
    )
    monkeypatch.setattr(
        predecir.TimeSeriesDataSet,
        "from_dataset",
        lambda *args, **kwargs: DatasetPrediccion(),
    )
    monkeypatch.setattr(predecir, "_PESO_POSITIVO", 1.0)

    resultados, _ = predecir.predecir_lote("2026-10-22")

    assert len(resultados) == 50
    assert resultados[0]["probabilidad"] < 0.50
    assert resultados[0]["en_desabasto"] == 0
