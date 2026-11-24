"""Inferencia local en CPU y evaluación rodante del TFT de ZENIT.

El modelo nuevo clasifica el evento semanal directamente. La lectura de
checkpoints antiguos conserva su comportamiento y advierte su aproximación.
"""
from __future__ import annotations

import time
import hashlib
import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from pytorch_forecasting import TimeSeriesDataSet
from modelo.red import TFTZenit as TemporalFusionTransformer
from sklearn.metrics import f1_score, precision_score, recall_score, brier_score_loss, average_precision_score

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

# Suprimir advertencias redundantes de bibliotecas de inferencia
warnings.filterwarnings("ignore", category=UserWarning, module="lightning")
warnings.filterwarnings("ignore", category=UserWarning, module="pytorch_forecasting")
warnings.filterwarnings("ignore", category=FutureWarning, module="lightning")

HILOS_CPU = 1

_MODELO_CACHE: Optional[Tuple[TemporalFusionTransformer, TimeSeriesDataSet, pd.DataFrame]] = None
_PESO_POSITIVO: Optional[float] = None
_CACHE_KEY = None
_METADATA = {}


_WARNED_CHECKPOINT = False


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


def cargar_modelo(csv_path=None, ckpt_path=None) -> Tuple[TemporalFusionTransformer, TimeSeriesDataSet, pd.DataFrame]:
    """Carga escaladores del checkpoint y refresca al cambiar datos o modelo."""
    global _MODELO_CACHE, _PESO_POSITIVO, _CACHE_KEY, _METADATA
    limitar_hilos_cpu()
    ruta_ckpt, ruta_csv = Path(ckpt_path or CKPT_PATH).resolve(), Path(csv_path or CSV_PATH).resolve()
    if not ruta_ckpt.is_file():
        raise FileNotFoundError(f"No se encontró el checkpoint TFT en {ruta_ckpt}. Entrena con: python -m modelo.entrenar_tft tft")
    clave = (str(ruta_ckpt), ruta_ckpt.stat().st_mtime_ns, ruta_ckpt.stat().st_size,
             str(ruta_csv), ruta_csv.stat().st_mtime_ns, ruta_csv.stat().st_size)
    if _MODELO_CACHE is not None and clave == _CACHE_KEY:
        return _MODELO_CACHE
    df = preparar_datos(ruta_csv)
    modelo = TemporalFusionTransformer.load_from_checkpoint(str(ruta_ckpt), map_location="cpu")
    metadata = dict(modelo.hparams.get("zenit_metadata", {}))
    huella = hashlib.sha256(ruta_csv.read_bytes()).hexdigest()
    if metadata and metadata.get("dataset_sha256") != huella:
        raise ValueError("El dataset no coincide con la huella del entrenamiento. Reentrena y valida antes de usarlo.")
    parametros = modelo.hparams.get("dataset_parameters")
    if parametros is None:
        raise ValueError("El checkpoint no contiene los normalizadores del entrenamiento.")
    dataset = TimeSeriesDataSet.from_parameters(parametros, df[df.time_idx < metadata.get("fin_ajuste_exclusivo", DIAS_ENTRENAMIENTO)], stop_randomization=True)
    modelo.eval()
    _METADATA = metadata or {"objetivo": "diario_legacy", "modelo_version": "legacy-" + hashlib.sha256(ruta_ckpt.read_bytes()).hexdigest()[:12], "dataset_sha256": huella}
    _PESO_POSITIVO = float(metadata.get("peso_positivo", getattr(modelo.loss, "peso_positivo", 1.0)))
    _CACHE_KEY, _MODELO_CACHE = clave, (modelo, dataset, df)
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


def predecir_lote(fecha_corte: str, csv_path=None, ckpt_path=None) -> Tuple[List[Dict[str, object]], float]:
    """Ejecuta la inferencia del TFT para los 50 productos en una fecha de corte."""
    modelo, dataset_entrenamiento, df = cargar_modelo(csv_path, ckpt_path) if csv_path is not None or ckpt_path is not None else cargar_modelo()
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
    with torch.inference_mode():
        salida = modelo.predict(
            dataloader,
            mode="raw",
            return_x=False,
            return_index=True,
            trainer_kwargs={"accelerator": "cpu", "logger": False, "enable_progress_bar": False},
        )
    tiempo_ms = (time.perf_counter() - inicio) * 1000.0

    logits = _extraer_logits(salida)
    indice = getattr(salida, "index", None)
    if isinstance(indice, pd.DataFrame):
        productos = indice["producto"].tolist()
    if len(productos) != logits.shape[0] or len(set(productos)) != len(productos):
        raise RuntimeError("El TFT devolvió ventanas duplicadas o una salida incompleta.")
    peso = _PESO_POSITIVO
    if peso is None:
        _, _, peso = calcular_peso_positivo(df[df["time_idx"] < DIAS_ENTRENAMIENTO])
    if _METADATA.get("objetivo") == "evento_semanal_v1":
        ponderada = torch.softmax(logits.float().mean(dim=1), dim=-1)[:, 1].cpu().numpy()
        prob_semanal = corregir_probabilidad_ponderada(ponderada, peso)
    else:
        global _WARNED_CHECKPOINT
        if not _WARNED_CHECKPOINT:
            warnings.warn("Checkpoint antiguo: riesgo semanal aproximado bajo independencia diaria. Reentrena para evento semanal directo.", RuntimeWarning)
            _WARNED_CHECKPOINT = True
        ponderada = torch.softmax(logits.float(), dim=-1)[..., 1].cpu().numpy()
        prob_semanal = agregar_probabilidad_7d(corregir_probabilidad_ponderada(ponderada, peso))
    if not np.isfinite(prob_semanal).all() or ((prob_semanal < 0) | (prob_semanal > 1)).any():
        raise RuntimeError("El TFT produjo probabilidades inválidas.")

    resultados: List[Dict[str, object]] = []
    for producto, prob in zip(productos, prob_semanal.tolist()):
        prob_float = float(prob)
        resultados.append({
            "producto": producto,
            "cuadrante_kraljic": cuadrantes[producto],
            "probabilidad": prob_float,
            "en_desabasto": int(prob_float >= UMBRAL_ALERTA),
            "fecha_corte": fecha_corte,
            "modelo_version": _METADATA.get("modelo_version", "sin-version"),
            "dataset_sha256": _METADATA.get("dataset_sha256", ""),
            "objetivo": _METADATA.get("objetivo", "diario_legacy"),
        })

    return resultados, tiempo_ms


def resumir_metricas(y_real, probabilidades):
    """Métricas al umbral fijo; calibración descriptiva, sin ajustar con prueba."""
    reales = np.asarray(y_real, dtype=int)
    prob = np.asarray(probabilidades, dtype=float)
    if reales.size == 0 or reales.shape != prob.shape or not np.isfinite(prob).all() or ((prob < 0) | (prob > 1)).any():
        raise ValueError("La evaluación necesita etiquetas y probabilidades válidas.")
    pred = prob >= UMBRAL_ALERTA
    calibracion = []
    for lo, hi in zip(np.linspace(0, 1, 6)[:-1], np.linspace(0, 1, 6)[1:]):
        mascara = (prob >= lo) & ((prob < hi) if hi < 1 else (prob <= hi))
        if mascara.any():
            calibracion.append({"desde": float(lo), "hasta": float(hi), "casos": int(mascara.sum()),
                "riesgo_medio": float(prob[mascara].mean()), "frecuencia_real": float(reales[mascara].mean())})
    return {
        "total_evaluados": int(len(reales)), "positivos_reales": int(reales.sum()), "positivos_predichos": int(pred.sum()),
        "tp": int(((reales == 1) & pred).sum()), "fp": int(((reales == 0) & pred).sum()),
        "fn": int(((reales == 1) & ~pred).sum()), "tn": int(((reales == 0) & ~pred).sum()),
        "precision": float(precision_score(reales, pred, zero_division=0)),
        "recall": float(recall_score(reales, pred, zero_division=0)),
        "f1": float(f1_score(reales, pred, zero_division=0)),
        "brier": float(brier_score_loss(reales, prob)),
        "pr_auc": float(average_precision_score(reales, prob)) if reales.sum() else None,
        "calibracion": calibracion,
    }


def evaluar_periodo(csv_path=CSV_PATH, ckpt_path=None, inicio=DIAS_ENTRENAMIENTO, fin=None):
    """Las etiquetas futuras caen íntegramente en [inicio, fin). Ventanas solapadas."""
    df = preparar_datos(csv_path)
    fin = int(df.time_idx.max()) + 1 if fin is None else fin
    if inicio < LONGITUD_ENCODER or fin > int(df.time_idx.max()) + 1 or fin - inicio < HORIZONTE:
        raise ValueError("El periodo necesita historia suficiente y siete días futuros completos.")
    cortes = range(inicio - 1, fin - HORIZONTE)
    reales, probabilidades, referencia, detalle = [], [], [], []
    esperados = set(df.producto.unique())
    for corte in cortes:
        fecha = df.loc[df.time_idx == corte, "fecha"].iloc[0].strftime("%Y-%m-%d")
        if ckpt_path is None and Path(csv_path).resolve() == Path(CSV_PATH).resolve():
            predicciones, _ = predecir_lote(fecha)
        else:
            predicciones, _ = predecir_lote(fecha, csv_path=csv_path, ckpt_path=ckpt_path)
        if len(predicciones) != len(esperados) or {p["producto"] for p in predicciones} != esperados:
            raise RuntimeError("Evaluación incompleta: faltan productos o hay duplicados.")
        futuro = df[(df.time_idx > corte) & (df.time_idx <= corte + HORIZONTE)].groupby("producto").en_desabasto.max().to_dict()
        actual = df[df.time_idx == corte].set_index("producto")
        for item in predicciones:
            producto = item["producto"]
            real, prob = int(futuro[producto]), float(item["probabilidad"])
            base = int(actual.loc[producto, "dias_cobertura"] < 7)
            reales.append(real); probabilidades.append(prob); referencia.append(base)
            detalle.append({"producto": producto, "fecha_corte": fecha, "real": real, "probabilidad": prob})
    reporte = {**resumir_metricas(reales, probabilidades), "origenes_evaluados": len(cortes),
        "inicio_etiquetas": inicio, "fin_etiquetas_exclusivo": fin, "umbral": UMBRAL_ALERTA,
        "referencia_cobertura": resumir_metricas(reales, referencia),
        "por_producto": {}, "detalle": detalle,
        "nota": "Ventanas solapadas; los casos no son independientes. No mide demanda no atendida ni efecto de intervenciones.",
    }
    for producto in sorted(esperados):
        filas = [r for r in detalle if r["producto"] == producto]
        reporte["por_producto"][producto] = resumir_metricas([r["real"] for r in filas], [r["probabilidad"] for r in filas])
    episodios = []
    for producto, grupo in df.groupby("producto"):
        grupo = grupo.sort_values("time_idx")
        comienzos = grupo[(grupo.en_desabasto == 1) & (grupo.en_desabasto.shift(1, fill_value=0) == 0)]
        for evento in comienzos.itertuples():
            if not inicio <= evento.time_idx < fin:
                continue
            fecha_evento = evento.fecha
            avisos = [r for r in detalle if r["producto"] == producto and r["probabilidad"] >= UMBRAL_ALERTA
                and 0 < (fecha_evento - pd.Timestamp(r["fecha_corte"])).days <= HORIZONTE]
            episodios.append({"producto": producto, "inicio": fecha_evento.strftime("%Y-%m-%d"),
                "detectado": bool(avisos), "anticipacion_dias": max(
                    ((fecha_evento - pd.Timestamp(r["fecha_corte"])).days for r in avisos), default=None)})
    reporte["episodios"] = episodios
    reporte["episodios_detectados"] = sum(e["detectado"] for e in episodios)
    reporte["episodios_totales"] = len(episodios)
    return reporte


def evaluar_ultimos_27_dias(csv_path=None, ckpt_path=None) -> Dict[str, object]:
    ruta = Path(csv_path or CSV_PATH)
    reporte = evaluar_periodo(ruta, ckpt_path)
    if ckpt_path is not None:
        reporte["ckpt_path"] = str(Path(ckpt_path).resolve())
        reporte["dataset_sha256"] = hashlib.sha256(ruta.read_bytes()).hexdigest()
        reporte["modelo_version"] = _METADATA.get("modelo_version", "sin-version")
        Path(ckpt_path).with_suffix(".evaluacion.json").write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")
    return reporte


if __name__ == "__main__":
    print(json.dumps(evaluar_ultimos_27_dias(), indent=2, ensure_ascii=False))
