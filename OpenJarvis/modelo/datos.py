"""Preparación de datos y construcción del TimeSeriesDataSet para el TFT de ZENIT.

Conserva la etiqueta diaria observada y entrena su evento semanal.
La división temporal es 49 días de ajuste, 14 de validación y 27 de prueba.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from pytorch_forecasting import TimeSeriesDataSet
from pytorch_forecasting.data import NaNLabelEncoder
from pytorch_forecasting.metrics import CrossEntropy


class CrossEntropyPonderada(CrossEntropy):
    """Entropía cruzada binaria ponderada por la proporción negativos/positivos."""

    def __init__(self, peso_positivo: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.peso_positivo = float(peso_positivo)

    def loss(self, y_pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pesos = torch.tensor(
            [1.0, self.peso_positivo],
            dtype=y_pred.dtype,
            device=y_pred.device,
        )
        return F.cross_entropy(
            y_pred.view(-1, y_pred.size(-1)),
            target.view(-1),
            weight=pesos,
            reduction="none",
        ).view(-1, target.size(-1))

class CrossEntropySemanal(CrossEntropyPonderada):
    """Clasifica el evento semanal directamente, sin independencia diaria."""

    def loss(self, y_pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pesos = y_pred.new_tensor([1.0, self.peso_positivo])
        perdida = F.cross_entropy(
            y_pred.mean(dim=1), target.max(dim=1).values.long(),
            weight=pesos, reduction="none",
        )
        return perdida[:, None].expand(-1, target.size(1))


ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT_DIR / "data" / "ventas.csv"
CKPT_PATH = Path(__file__).resolve().parent / "zenith_tft.ckpt"

HORIZONTE = 7
DIAS_ENTRENAMIENTO = 63
DIAS_VALIDACION = 14
FIN_AJUSTE = DIAS_ENTRENAMIENTO - DIAS_VALIDACION
LONGITUD_ENCODER = 28
UMBRAL_ALERTA = 0.50

COLUMNAS_REQUERIDAS = (
    "producto",
    "fecha",
    "unidades_vendidas",
    "existencia",
    "cuadrante_kraljic",
    "requiere_refrigeracion",
    "fecha_caducidad",
    "temperatura",
)


def preparar_datos(csv_path: Union[str, Path] = CSV_PATH) -> pd.DataFrame:
    """Carga y transforma el CSV canónico en un DataFrame listo para el TFT."""
    ruta = Path(csv_path)
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de ventas: {ruta}")

    df = pd.read_csv(ruta)
    faltantes = [col for col in COLUMNAS_REQUERIDAS if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en {ruta.name}: {faltantes}")

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    if df.empty or df[list(COLUMNAS_REQUERIDAS)].isna().any().any():
        raise ValueError("El historial está vacío o contiene valores nulos.")
    if df.duplicated(["producto", "fecha"]).any():
        raise ValueError("Hay registros duplicados por producto y fecha.")
    for columna in ("unidades_vendidas", "existencia"):
        valores = pd.to_numeric(df[columna], errors="raise")
        if not np.isfinite(valores).all() or (valores < 0).any() or (valores % 1 != 0).any():
            raise ValueError(f"{columna} debe contener enteros no negativos.")
    for _, grupo in df.groupby("producto"):
        diferencias = grupo["fecha"].sort_values().diff().dropna()
        if not (diferencias == pd.Timedelta(days=1)).all():
            raise ValueError("El historial debe tener días consecutivos por producto.")
    df = df.sort_values(["producto", "fecha"]).reset_index(drop=True)

    fecha_min = df["fecha"].min()
    df["time_idx"] = (df["fecha"] - fecha_min).dt.days.astype(int)
    df["dia_semana"] = df["fecha"].dt.weekday.astype(int)
    df["unidades_vendidas"] = df["unidades_vendidas"].astype(float)
    df["existencia"] = df["existencia"].astype(float)
    df["temperatura"] = df["temperatura"].astype(float)
    df["en_desabasto"] = (df["existencia"] == 0).astype(int)
    df["producto"] = df["producto"].astype(str)
    df["cuadrante_kraljic"] = df["cuadrante_kraljic"].astype(str)
    df["requiere_refrigeracion"] = df["requiere_refrigeracion"].astype(int).astype(str)
    df["es_quincena"] = df["fecha"].dt.day.isin([1, 15, 16, 30]).astype(float)

    dias_sin_resurtido = []
    existencia_relativa = []
    dias_cobertura = []
    for _, grupo in df.groupby("producto", sort=False):
        exist = grupo["existencia"].to_numpy(dtype=float)
        ventas = grupo["unidades_vendidas"].to_numpy(dtype=float)
        max_acumulado = np.maximum.accumulate(np.maximum(exist, 1.0))
        rel = exist / max_acumulado
        ventas_media_7d = pd.Series(ventas).rolling(7, min_periods=1).mean().to_numpy()
        cobertura = np.clip(exist / np.maximum(ventas_media_7d, 0.5), 0.0, 30.0)

        sin_resurtido = np.zeros(len(exist), dtype=float)
        contador = 0
        for idx in range(1, len(exist)):
            contador = 0 if exist[idx] > exist[idx - 1] else contador + 1
            sin_resurtido[idx] = float(contador)

        dias_sin_resurtido.append(sin_resurtido)
        existencia_relativa.append(rel)
        dias_cobertura.append(cobertura)

    df["dias_sin_resurtido"] = np.concatenate(dias_sin_resurtido)
    df["existencia_relativa"] = np.concatenate(existencia_relativa)
    df["dias_cobertura"] = np.concatenate(dias_cobertura)
    return df


def calcular_peso_positivo(df_entrenamiento: pd.DataFrame) -> Tuple[int, int, float]:
    """Calcula positivos, negativos y el peso positivos = negativos / positivos.

    Se calcula exclusivamente sobre el bloque de entrenamiento (primeros 63 días).
    """
    positivos = int((df_entrenamiento["en_desabasto"] == 1).sum())
    negativos = int((df_entrenamiento["en_desabasto"] == 0).sum())
    if positivos <= 0:
        raise ValueError("El bloque de entrenamiento no contiene casos positivos de desabasto.")
    peso_positivo = float(negativos) / float(positivos)
    return positivos, negativos, peso_positivo


def crear_dataset_entrenamiento(df: pd.DataFrame, fin: int = DIAS_ENTRENAMIENTO, usar_kraljic: bool = True) -> Tuple[TimeSeriesDataSet, pd.DataFrame, float]:
    """Construye el TimeSeriesDataSet con los primeros 63 días del dataset canónico."""
    df_entrenamiento = df[df["time_idx"] < fin].copy()
    _, _, peso_positivo = calcular_peso_positivo(df_entrenamiento)

    dataset = TimeSeriesDataSet(
        df_entrenamiento,
        time_idx="time_idx",
        target="en_desabasto",
        group_ids=["producto"],
        min_encoder_length=LONGITUD_ENCODER,
        max_encoder_length=LONGITUD_ENCODER,
        min_prediction_length=HORIZONTE,
        max_prediction_length=HORIZONTE,
        static_categoricals=(["cuadrante_kraljic"] if usar_kraljic else []) + ["requiere_refrigeracion"],
        time_varying_known_reals=["dia_semana", "es_quincena"],
        time_varying_unknown_reals=[
            "unidades_vendidas",
            "existencia",
            "existencia_relativa",
            "dias_cobertura",
            "dias_sin_resurtido",
            "temperatura",
        ],
        target_normalizer=NaNLabelEncoder(),
        add_relative_time_idx=True,
        add_target_scales=False,
        add_encoder_length=False,
    )
    return dataset, df_entrenamiento, peso_positivo


def crear_particiones_temporales(df: pd.DataFrame):
    """Ajuste 0..48, etiquetas de validación 49..62, prueba 63..89.

    Escaladores ajustados solo con entrenamiento. Se permite historia anterior
    en validación, nunca etiquetas de validación en el ajuste.
    """
    if df.time_idx.max() < DIAS_ENTRENAMIENTO - 1:
        raise ValueError("Se necesitan al menos 63 días para ajuste y validación.")
    entrenamiento, _, _ = crear_dataset_entrenamiento(df, FIN_AJUSTE, usar_kraljic=False)
    validacion = TimeSeriesDataSet.from_dataset(
        entrenamiento, df[df.time_idx < DIAS_ENTRENAMIENTO].copy(),
        min_prediction_idx=FIN_AJUSTE, stop_randomization=True,
    )
    positivos = sum(int(y[0].max().item()) for _, y in entrenamiento)
    negativos = len(entrenamiento) - positivos
    if positivos == 0 or negativos == 0:
        raise ValueError("El ajuste necesita ventanas positivas y negativas.")
    return entrenamiento, validacion, negativos / positivos, positivos, negativos
