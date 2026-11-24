"""Entrenamiento semanal versionado con validación temporal independiente."""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import lightning.pytorch as pl
import torch
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger
from modelo.red import TFTZenit as TemporalFusionTransformer

from modelo.datos import (
    CKPT_PATH, FIN_AJUSTE, DIAS_ENTRENAMIENTO, CrossEntropySemanal,
    crear_particiones_temporales, preparar_datos,
)
from modelo.predecir import evaluar_periodo, limitar_hilos_cpu


def entrenar_validado(csv_path, ckpt_path, hidden_size, attention_head_size,
                     dropout, learning_rate, batch_size, max_epochs, accelerator, seed):
    """Guarda la mejor candidata; no sustituye silenciosamente el modelo activo."""
    if min(max_epochs, batch_size, hidden_size, attention_head_size) < 1:
        raise ValueError("Épocas, batch, tamaño y cabezas deben ser positivos.")
    if not 0 <= dropout < 1 or learning_rate <= 0:
        raise ValueError("Dropout debe estar en [0, 1) y learning rate debe ser positivo.")
    limitar_hilos_cpu()
    pl.seed_everything(seed, workers=True)
    csv_path, ckpt_path = Path(csv_path).resolve(), Path(ckpt_path).resolve()
    df = preparar_datos(csv_path)
    entrenamiento, validacion, peso, positivos, negativos = crear_particiones_temporales(df)
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ckpt_path.parent / "versiones" / version
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "modelo_version": version, "objetivo": "evento_semanal_v1",
        "dataset_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "peso_positivo": peso, "fin_ajuste_exclusivo": FIN_AJUSTE,
        "fin_validacion_exclusivo": DIAS_ENTRENAMIENTO, "umbral": 0.50,
        "semilla": seed, "python": sys.version, "torch": str(torch.__version__),
        "lightning": pl.__version__,
        "hiperparametros": {"hidden_size": hidden_size, "heads": attention_head_size,
            "dropout": dropout, "learning_rate": learning_rate, "batch_size": batch_size},
    }
    tft = TemporalFusionTransformer.from_dataset(
        entrenamiento, learning_rate=learning_rate, hidden_size=hidden_size,
        attention_head_size=attention_head_size, dropout=dropout,
        hidden_continuous_size=max(4, hidden_size // 2), output_size=2,
        loss=CrossEntropySemanal(peso_positivo=peso), optimizer="adam",
        logging_metrics=torch.nn.ModuleList(),
        log_interval=-1, reduce_on_plateau_patience=4,
    )
    tft.hparams["zenit_metadata"] = metadata
    mejor = ModelCheckpoint(dirpath=run_dir, filename="mejor", monitor="val_loss", mode="min", save_top_k=1)
    entrenador = pl.Trainer(
        max_epochs=max_epochs,
        accelerator="gpu" if accelerator.lower() in ("gpu", "cuda") and torch.cuda.is_available() else "cpu",
        devices=1, gradient_clip_val=0.5, deterministic=True,
        callbacks=[mejor, EarlyStopping(monitor="val_loss", mode="min", patience=8, min_delta=1e-4)],
        logger=CSVLogger(str(run_dir), name="curvas"), enable_model_summary=False,
        enable_progress_bar=False, num_sanity_val_steps=0, log_every_n_steps=1,
    )
    entrenador.fit(
        tft, train_dataloaders=entrenamiento.to_dataloader(train=True, batch_size=batch_size, num_workers=0, drop_last=False),
        val_dataloaders=validacion.to_dataloader(train=False, batch_size=batch_size, num_workers=0),
    )
    if not mejor.best_model_path:
        raise RuntimeError("No se generó un checkpoint válido de validación.")
    metricas = evaluar_periodo(csv_path, Path(mejor.best_model_path), FIN_AJUSTE, DIAS_ENTRENAMIENTO)
    resumen = {
        **metadata, "ckpt_path": mejor.best_model_path, "csv_path": str(csv_path),
        "checkpoint_sha256": hashlib.sha256(Path(mejor.best_model_path).read_bytes()).hexdigest(),
        "epocas_ejecutadas": entrenador.current_epoch,
        "mejor_val_loss": float(mejor.best_model_score),
        "ventanas_ajuste": len(entrenamiento), "ventanas_validacion": len(validacion),
        "positivos_entrenamiento": positivos, "negativos_entrenamiento": negativos,
        "validacion": metricas,
        # Salvaguarda operativa; diez positivos tampoco garantizan significancia.
        "criterios_activacion": {"f1_minimo": 0.75, "positivos_validacion_minimos": 10},
        "apto_validacion": metricas["f1"] >= 0.75 and metricas["positivos_reales"] >= 10,
        "activo": False,
    }
    (run_dir / "entrenamiento.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumen


def activar_modelo(candidato: Path, destino: Path = CKPT_PATH):
    """Conserva respaldo y activa únicamente una candidata validada."""
    candidato, destino = Path(candidato).resolve(), Path(destino).resolve()
    reporte = json.loads((candidato.parent / "entrenamiento.json").read_text(encoding="utf-8"))
    if not reporte.get("apto_validacion") or Path(reporte["ckpt_path"]).resolve() != candidato:
        raise ValueError("La candidata no cumple F1 >= 0.75 y al menos 10 positivos de validación.")
    metricas = reporte["validacion"]
    if metricas["f1"] < 0.75 or metricas["positivos_reales"] < 10:
        raise ValueError("La validación no tiene calidad o positivos suficientes.")
    if hashlib.sha256(candidato.read_bytes()).hexdigest() != reporte["checkpoint_sha256"]:
        raise ValueError("El checkpoint cambió después de validarse.")
    if hashlib.sha256(Path(reporte["csv_path"]).read_bytes()).hexdigest() != reporte["dataset_sha256"]:
        raise ValueError("El dataset cambió desde el entrenamiento.")
    if destino.exists():
        respaldo = destino.parent / "versiones" / ("respaldo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        respaldo.mkdir(parents=True, exist_ok=False)
        shutil.copy2(destino, respaldo / destino.name)
    temporal = destino.with_suffix(".tmp")
    shutil.copy2(candidato, temporal)
    temporal.replace(destino)
