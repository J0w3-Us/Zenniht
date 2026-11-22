"""Medición reproducible de rendimiento del TFT local (Hito de Procesamiento).

Uso desde OpenJarvis/:
    python -m modelo.medir_rendimiento

Separa la carga inicial del checkpoint del tiempo de inferencia por lote,
ejecuta 1 pasada de calentamiento y mide 30 lotes de 50 productos en CPU.
"""
from __future__ import annotations

import platform
import time
from typing import Dict, List

import numpy as np

from modelo import predecir

FECHA_CORTE_DEMO = "2026-10-22"
REPETICIONES = 30
UMBRAL_MS = 1000.0


def medir_rendimiento(
    fecha_corte: str = FECHA_CORTE_DEMO,
    repeticiones: int = REPETICIONES,
) -> Dict[str, object]:
    """Mide carga de checkpoint, inferencia TFT (p50/p95), llamada completa y CPU."""
    predecir._MODELO_CACHE = None

    inicio_carga = time.perf_counter()
    predecir.cargar_modelo()
    tiempo_carga_ms = (time.perf_counter() - inicio_carga) * 1000.0

    # Pasada de calentamiento fuera de la muestra medida.
    predecir.predecir_lote(fecha_corte)

    tiempos_tft_ms: List[float] = []
    tiempos_totales_ms: List[float] = []

    cpu_inicio = time.process_time()
    pared_inicio = time.perf_counter()
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        resultados, tft_ms = predecir.predecir_lote(fecha_corte)
        total_ms = (time.perf_counter() - t0) * 1000.0
        if len(resultados) != 50:
            raise RuntimeError(f"Se esperaban 50 productos y se obtuvieron {len(resultados)}.")
        tiempos_tft_ms.append(tft_ms)
        tiempos_totales_ms.append(total_ms)
    pared_total = time.perf_counter() - pared_inicio
    cpu_total = time.process_time() - cpu_inicio

    nucleos_equivalentes = cpu_total / pared_total if pared_total > 0 else 0.0
    p50_tft = float(np.percentile(tiempos_tft_ms, 50))
    p95_tft = float(np.percentile(tiempos_tft_ms, 95))
    p50_total = float(np.percentile(tiempos_totales_ms, 50))
    p95_total = float(np.percentile(tiempos_totales_ms, 95))

    return {
        "equipo": platform.processor() or platform.machine(),
        "fecha_corte": fecha_corte,
        "repeticiones": repeticiones,
        "hilos_cpu": predecir.HILOS_CPU,
        "carga_checkpoint_ms": round(tiempo_carga_ms, 2),
        "tft_p50_ms": round(p50_tft, 2),
        "tft_p95_ms": round(p95_tft, 2),
        "llamada_completa_p50_ms": round(p50_total, 2),
        "llamada_completa_p95_ms": round(p95_total, 2),
        "nucleos_equivalentes_promedio": round(nucleos_equivalentes, 2),
        "cumple_umbral_1000ms": p95_tft < UMBRAL_MS,
    }


if __name__ == "__main__":
    resultado = medir_rendimiento()
    print("Medición de rendimiento ZENIT (TFT CPU):")
    for clave, valor in resultado.items():
        print(f"  {clave}: {valor}")
