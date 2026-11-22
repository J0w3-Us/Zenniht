"""Inferencia local en CPU y evaluación rodante del TFT de ZENIT.

Reglas congeladas:
- Único modelo: Temporal Fusion Transformer (pytorch-forecasting, hidden_size=16, CPU).
- Límite de 1 hilo intraoperatorio y 1 interoperativo en PyTorch.
- Corrección de probabilidad por el peso de clase positivo antes de agregar el
  riesgo semanal: 1 - producto(1 - p_diaria).
- Sin respuestas prefabricadas ni respaldos: si falta el checkpoint, lanza error.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from sklearn.metrics import f1_score, precision_score, recall_score

from modelo.datos import (
    CKPT_PATH,
    CSV_PATH,
    DIAS_ENTRENAMIENTO,
    HORIZONTE,
    LONGITUD_ENCODER,
    UMBRAL_ALERTA,
    calcular_peso_positivo,
    crear_dataset_entrenamiento,
    preparar_datos,
)

HILOS_CPU = 1

_MODELO_CACHE: Optional[Tuple[TemporalFusionTransformer, TimeSeriesDataSet, pd.DataFrame]] = None
_PESO_POSITIVO: Optional[float] = None


def limitar_hilos_cpu() -> None:
    """Limita PyTorch a un hilo intraoperatorio y uno interoperativo."""
    torch.set_num_threads(HILOS_CPU)
    if torch.get_num_interop_threads() != HILOS_CPU:
        try:
            torch.set_num_interop_threads(HILOS_CPU)
        except RuntimeError:
            # PyTorch no permite cambiar interop_threads una vez iniciado trabajo paralelo.
            pass


def corregir_probabilidad_ponderada(
    probabilidades: np.ndarray,
    peso_positivo: float,
) -> np.ndarray:
    """Corrige el sesgo de probabilidades salidas de CrossEntropy ponderado."""
    if peso_positivo <= 0:
        raise ValueError("El peso positivo debe ser mayor que cero.")
    p = np.asarray(probabilidades, dtype=np.float64)
    numerador = p
    denominador = p + float(peso_positivo) * (1.0 - p)
    return np.divide(
        numerador,
        denominador,
        out=np.zeros_like(numerador, dtype=np.float64),
        where=denominador > 0,
    )


def agregar_probabilidad_7d(probabilidades: np.ndarray) -> np.ndarray:
    """Agrega probabilidades diarias de quiebre en riesgo semanal a 7 días."""
    arr = np.asarray(probabilidades, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != HORIZONTE:
        raise ValueError("Se requieren probabilidades diarias con horizonte de 7 días.")
    return 1.0 - np.prod(1.0 - arr, axis=1)


def cargar_modelo() -> Tuple[TemporalFusionTransformer, TimeSeriesDataSet, pd.DataFrame]:
    """Carga y mantiene en caché el checkpoint local del TFT en CPU."""
    global _MODELO_CACHE, _PESO_POSITIVO

    limitar_hilos_cpu()
    if _MODELO_CACHE is not None:
        return _MODELO_CACHE

    ruta_ckpt = Path(CKPT_PATH)
    if not ruta_ckpt.is_file():
        raise FileNotFoundError(
            f"No se encontró el checkpoint TFT en {ruta_ckpt}. "
            "Entrena el modelo primero con: python -m modelo.entrenar_tft"
        )

    df = preparar_datos(CSV_PATH)
    dataset_entrenamiento, _, peso_positivo = crear_dataset_entrenamiento(df)
    modelo = TemporalFusionTransformer.load_from_checkpoint(
        str(ruta_ckpt),
        map_location="cpu",
    )
    modelo.eval()

    _PESO_POSITIVO = peso_positivo
    _MODELO_CACHE = (modelo, dataset_entrenamiento, df)
    return _MODELO_CACHE


def _construir_dataframe_prediccion(
    df: pd.DataFrame,
    fecha_corte: str,
) -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
    """Prepara las ventanas históricas (28 días) y los 7 días futuros sin fuga de datos."""
    corte_ts = pd.Timestamp(fecha_corte)
    fechas_disponibles = pd.Index(df["fecha"].unique()).sort_values()
    if corte_ts not in fechas_disponibles:
        raise ValueError(
            f"La fecha de corte {fecha_corte} no existe en el dataset canónico."
        )

    corte_idx = int(df.loc[df["fecha"] == corte_ts, "time_idx"].iloc[0])
    inicio_idx = corte_idx - (LONGITUD_ENCODER - 1)
    if inicio_idx < int(df["time_idx"].min()):
        raise ValueError(
            f"La fecha de corte {fecha_corte} requiere al menos {LONGITUD_ENCODER} días de historia."
        )

    historia = df[(df["time_idx"] >= inicio_idx) & (df["time_idx"] <= corte_idx)].copy()
    historia = historia.sort_values(["producto", "time_idx"]).reset_index(drop=True)

    ultimo_dia = historia[historia["time_idx"] == corte_idx].sort_values("producto")
    productos = ultimo_dia["producto"].tolist()
    cuadrantes = dict(zip(ultimo_dia["producto"], ultimo_dia["cuadrante_kraljic"]))

    filas_futuras: List[Dict[str, object]] = []
    for paso in range(1, HORIZONTE + 1):
        fecha_futura = corte_ts + pd.Timedelta(days=paso)
        dia_semana = int(fecha_futura.weekday())
        for fila in ultimo_dia.itertuples(index=False):
            filas_futuras.append({
                "producto": fila.producto,
                "fecha": fecha_futura,
                "time_idx": corte_idx + paso,
                "cuadrante_kraljic": fila.cuadrante_kraljic,
                "unidades_vendidas": 0.0,
                "existencia": 0.0,
                "existencia_relativa": 0.0,
                "dias_cobertura": 0.0,
                "dias_sin_resurtido": 0.0,
                "temperatura": float(fila.temperatura),
                "en_desabasto": 0,
                "dia_semana": dia_semana,
                "es_quincena": float(fecha_futura.day in (1, 15, 16, 30)),
                "requiere_refrigeracion": str(fila.requiere_refrigeracion),
            })

    futuro = pd.DataFrame(filas_futuras)
    columnas_comunes = [col for col in historia.columns if col in futuro.columns]
    df_pred = pd.concat(
        [historia[columnas_comunes], futuro[columnas_comunes]],
        ignore_index=True,
    )
    df_pred = df_pred.sort_values(["producto", "time_idx"]).reset_index(drop=True)
    return df_pred, productos, cuadrantes


def _extraer_logits(salida: object) -> torch.Tensor:
    """Extrae el tensor de logits (N, 7, 2) desde la salida de TFT.predict."""
    if hasattr(salida, "output"):
        salida = salida.output
    if hasattr(salida, "prediction"):
        salida = salida.prediction
    elif isinstance(salida, dict) and "prediction" in salida:
        salida = salida["prediction"]
    if not isinstance(salida, torch.Tensor):
        salida = torch.as_tensor(salida)
    return salida


def predecir_lote(fecha_corte: str) -> Tuple[List[Dict[str, object]], float]:
    """Ejecuta la inferencia del TFT para los 50 productos en una fecha de corte."""
    modelo, dataset_entrenamiento, df = cargar_modelo()
    df_pred, productos, cuadrantes = _construir_dataframe_prediccion(df, fecha_corte)

    dataset_pred = TimeSeriesDataSet.from_dataset(
        dataset_entrenamiento,
        df_pred,
        predict=True,
        stop_randomization=True,
    )
    dataloader = dataset_pred.to_dataloader(
        train=False,
        batch_size=len(productos),
        num_workers=0,
    )

    inicio = time.perf_counter()
    with torch.no_grad():
        salida = modelo.predict(
            dataloader,
            mode="raw",
            return_x=False,
            trainer_kwargs={"accelerator": "cpu", "logger": False, "enable_progress_bar": False},
        )
    tiempo_ms = (time.perf_counter() - inicio) * 1000.0

    logits = _extraer_logits(salida)
    prob_diaria_ponderada = torch.softmax(logits.float(), dim=-1)[..., 1].detach().cpu().numpy()

    peso = _PESO_POSITIVO
    if peso is None:
        _, _, peso = calcular_peso_positivo(df[df["time_idx"] < DIAS_ENTRENAMIENTO])

    prob_diaria = corregir_probabilidad_ponderada(prob_diaria_ponderada, peso)
    prob_semanal = agregar_probabilidad_7d(prob_diaria)

    resultados: List[Dict[str, object]] = []
    for producto, prob in zip(productos, prob_semanal.tolist()):
        prob_float = float(prob)
        resultados.append({
            "producto": producto,
            "cuadrante_kraljic": cuadrantes[producto],
            "probabilidad": prob_float,
            "en_desabasto": int(prob_float >= UMBRAL_ALERTA),
            "fecha_corte": fecha_corte,
        })

    return resultados, tiempo_ms


def evaluar_ultimos_27_dias() -> Dict[str, object]:
    """Evalúa el F1-Score rodante sobre los últimos 27 días (21 cortes × 50 productos)."""
    df = preparar_datos(CSV_PATH)
    fechas_ordenadas = sorted(df["fecha"].unique())
    cortes = fechas_ordenadas[DIAS_ENTRENAMIENTO - 1 : len(fechas_ordenadas) - HORIZONTE]

    y_real: List[int] = []
    y_pred: List[int] = []

    for corte_ts in cortes:
        fecha_corte = pd.Timestamp(corte_ts).strftime("%Y-%m-%d")
        corte_idx = int(df.loc[df["fecha"] == corte_ts, "time_idx"].iloc[0])

        ventana_futura = df[
            (df["time_idx"] > corte_idx) & (df["time_idx"] <= corte_idx + HORIZONTE)
        ]
        quiebre_real_por_prod = (
            ventana_futura.groupby("producto")["en_desabasto"].max().to_dict()
        )

        predicciones, _ = predecir_lote(fecha_corte)
        for item in predicciones:
            producto = str(item["producto"])
            y_real.append(int(quiebre_real_por_prod[producto]))
            y_pred.append(int(float(item["probabilidad"]) >= UMBRAL_ALERTA))

    tp = sum(1 for r, p in zip(y_real, y_pred) if r == 1 and p == 1)
    fp = sum(1 for r, p in zip(y_real, y_pred) if r == 0 and p == 1)
    fn = sum(1 for r, p in zip(y_real, y_pred) if r == 1 and p == 0)
    tn = sum(1 for r, p in zip(y_real, y_pred) if r == 0 and p == 0)

    return {
        "origenes_evaluados": len(cortes),
        "total_evaluados": len(y_real),
        "positivos_reales": sum(y_real),
        "positivos_predichos": sum(y_pred),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": float(precision_score(y_real, y_pred, zero_division=0)),
        "recall": float(recall_score(y_real, y_pred, zero_division=0)),
        "f1": float(f1_score(y_real, y_pred, zero_division=0)),
    }


if __name__ == "__main__":
    reporte = evaluar_ultimos_27_dias()
    print("Evaluación rodante últimos 27 días:")
    for clave, valor in reporte.items():
        print(f"  {clave}: {valor}")
