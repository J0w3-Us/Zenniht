"""Entrenamiento local en CPU del Temporal Fusion Transformer (TFT) de ZENIT.

Restricciones obligatorias:
- Único modelo: TemporalFusionTransformer de pytorch-forecasting.
- hidden_size=16, CPU, horizonte de 7 días.
- Entrenamiento exclusivo con los primeros 63 días de data/ventas.csv.
- Objetivo diario: existencia == 0, con CrossEntropy ponderado por negativos/positivos.
- Guarda el checkpoint en modelo/zenith_tft.ckpt.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict

import lightning.pytorch as pl
import torch
from pytorch_forecasting import TemporalFusionTransformer

from modelo.datos import (
    CKPT_PATH,
    CSV_PATH,
    CrossEntropyPonderada,
    calcular_peso_positivo,
    crear_dataset_entrenamiento,
    preparar_datos,
)
from modelo.predecir import limitar_hilos_cpu

SEMILLA = 42
HIDDEN_SIZE = 16
ATTENTION_HEAD_SIZE = 2
DROPOUT = 0.1
LEARNING_RATE = 0.005
BATCH_SIZE = 128
MAX_EPOCHS = 45


def entrenar(
    csv_path: Path = CSV_PATH,
    ckpt_path: Path = CKPT_PATH,
    max_epochs: int = MAX_EPOCHS,
) -> Dict[str, object]:
    """Entrena el TFT en CPU con los primeros 63 días y guarda el checkpoint."""
    limitar_hilos_cpu()
    pl.seed_everything(SEMILLA, workers=True)
    warnings.filterwarnings("ignore", category=UserWarning)

    df = preparar_datos(csv_path)
    dataset_entrenamiento, df_entrenamiento, peso_positivo = crear_dataset_entrenamiento(df)
    positivos, negativos, _ = calcular_peso_positivo(df_entrenamiento)

    dataloader_entrenamiento = dataset_entrenamiento.to_dataloader(
        train=True,
        batch_size=BATCH_SIZE,
        num_workers=0,
    )

    perdida = CrossEntropyPonderada(peso_positivo=peso_positivo)

    tft = TemporalFusionTransformer.from_dataset(
        dataset_entrenamiento,
        learning_rate=LEARNING_RATE,
        hidden_size=HIDDEN_SIZE,
        attention_head_size=ATTENTION_HEAD_SIZE,
        dropout=DROPOUT,
        hidden_continuous_size=8,
        output_size=2,
        loss=perdida,
        optimizer="adam",
        log_interval=-1,
        reduce_on_plateau_patience=4,
    )

    entrenador = pl.Trainer(
        max_epochs=max_epochs,
        accelerator="cpu",
        devices=1,
        gradient_clip_val=0.5,
        enable_checkpointing=False,
        logger=False,
        enable_model_summary=False,
        enable_progress_bar=True,
        deterministic=True,
    )
    entrenador.fit(tft, train_dataloaders=dataloader_entrenamiento)

    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    entrenador.save_checkpoint(str(ckpt_path))

    return {
        "ckpt_path": str(ckpt_path),
        "positivos_entrenamiento": positivos,
        "negativos_entrenamiento": negativos,
        "peso_positivo": peso_positivo,
        "epocas": max_epochs,
        "cuda_disponible": bool(torch.cuda.is_available()),
    }


if __name__ == "__main__":
    resumen = entrenar()
    print("\nEntrenamiento TFT completado:")
    for clave, valor in resumen.items():
        print(f"  {clave}: {valor}")

    from modelo.predecir import evaluar_ultimos_27_dias

    reporte = evaluar_ultimos_27_dias()
    print("\nEvaluación en los últimos 27 días (21 cortes × 50 productos):")
    for clave, valor in reporte.items():
        print(f"  {clave}: {valor}")
