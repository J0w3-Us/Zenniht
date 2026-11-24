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
    monkeypatch.setattr(predecir, "limitar_hilos_cpu", lambda: None)

    with pytest.raises(FileNotFoundError, match="No se encontró el checkpoint TFT"):
        predecir.cargar_modelo()


def test_cargar_modelo_limita_hilos_cpu_incluso_con_modelo_en_cache(monkeypatch):
    cache = predecir.cargar_modelo()
    hilos_configurados = []
    monkeypatch.setattr(predecir, "limitar_hilos_cpu", lambda: hilos_configurados.append(1))

    assert predecir.cargar_modelo() is cache
    assert hilos_configurados == [predecir.HILOS_CPU]


def test_limitar_hilos_cpu_configura_ambos_limites(monkeypatch):
    hilos_intra = []
    hilos_inter = []
    monkeypatch.setattr(predecir.torch, "set_num_threads", hilos_intra.append)
    monkeypatch.setattr(predecir.torch, "get_num_interop_threads", lambda: 10)
    monkeypatch.setattr(predecir.torch, "set_num_interop_threads", hilos_inter.append)

    predecir.limitar_hilos_cpu()

    assert hilos_intra == [predecir.HILOS_CPU]
    assert hilos_inter == [predecir.HILOS_CPU]


def test_probabilidad_cercana_al_umbral_no_se_redondea_a_alerta(monkeypatch):
    fecha = pd.Timestamp("2026-10-22")
    filas = [
        {
            "producto": f"Producto {producto:02}",
            "fecha": fecha - pd.Timedelta(days=27 - dia),
            "time_idx": dia,
            "cuadrante_kraljic": "Estratégico",
            "unidades_vendidas": 1,
            "existencia": 1,
            "temperatura": 20.0,
            "en_desabasto": 0,
            "dia_semana": dia % 7,
            "requiere_refrigeracion": "0",
        }
        for producto in range(50)
        for dia in range(35)
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
    monkeypatch.setattr(predecir, "_METADATA", {"objetivo": "diario_legacy"})

    resultados, _ = predecir.predecir_lote("2026-10-22")

    assert len(resultados) == 50
    assert resultados[0]["probabilidad"] < 0.50
    assert resultados[0]["en_desabasto"] == 0
