"""Módulo de priorización Kraljic para ZENIT (Actividad 3).

El modelo TFT genera la probabilidad de desabasto; kraljic.py organiza
la prioridad visual y de gestión sin alterar la probabilidad calculada ni el umbral de 0.50.

Prioridad de atención según la matriz de Kraljic:
  1. Estratégico (alto impacto en salud/tratamientos crónicos, alto riesgo de suministro)
  2. Cuello de botella (impacto moderado, alto riesgo de suministro / temporada)
  3. Apalancamiento (alto volumen / rotación, bajo riesgo / muchos proveedores)
  4. No crítico (bajo impacto, bajo riesgo de suministro)
"""
from typing import Dict, List

ORDEN_KRALJIC = {
    "Estratégico": 1,
    "Cuello de botella": 2,
    "Apalancamiento": 3,
    "No crítico": 4,
}


def obtener_prioridad_kraljic(cuadrante: str) -> int:
    """Devuelve el orden numérico de prioridad del cuadrante."""
    return ORDEN_KRALJIC.get(cuadrante, 99)


def ordenar_alertas_kraljic(alertas: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Ordena las alertas de productos por prioridad Kraljic y luego por probabilidad descendente.
    
    No modifica ningún valor numérico ni la probabilidad del TFT.
    """
    return sorted(
        alertas,
        key=lambda item: (
            # 0 si está en desabasto (prob >= 0.50), 1 si no
            0 if float(item.get("probabilidad", 0.0)) >= 0.50 else 1,
            obtener_prioridad_kraljic(str(item.get("cuadrante_kraljic", ""))),
            -float(item.get("probabilidad", 0.0)),
            str(item.get("producto", ""))
        )
    )

