import numpy as np
import pandas as pd
import pytest

import db
from modelo import predecir
from modelo.datos import preparar_datos
from modelo.predecir import (
    agregar_probabilidad_7d,
    corregir_probabilidad_ponderada,
)


def test_objetivo_diario_refleja_existencia_cero(tmp_path):
    csv_path = tmp_path / "ventas.csv"
    pd.DataFrame({
        "producto": ["Producto A", "Producto A"],
        "fecha": ["2026-01-01", "2026-01-02"],
        "unidades_vendidas": [1, 0],
        "existencia": [2, 0],
        "cuadrante_kraljic": ["Estratégico", "Estratégico"],
        "requiere_refrigeracion": [0, 0],
        "fecha_caducidad": ["2027-01-01", "2027-01-01"],
        "temperatura": [20.0, 20.0],
    }).to_csv(csv_path, index=False)

    resultado = preparar_datos(csv_path)

    assert resultado["en_desabasto"].tolist() == [0, 1]


def test_agregar_probabilidad_de_quiebre_en_siete_dias():
    probabilidades = np.full((2, 7), 0.1)

    resultado = agregar_probabilidad_7d(probabilidades)

    assert resultado.tolist() == pytest.approx([1 - 0.9**7, 1 - 0.9**7])


def test_agregar_probabilidad_rechaza_horizonte_invalido():
    with pytest.raises(ValueError, match="7 días"):
        agregar_probabilidad_7d(np.full((2, 6), 0.1))


def test_corregir_probabilidad_de_entropia_ponderada():
    probabilidades_ponderadas = np.array([0.5])

    resultado = corregir_probabilidad_ponderada(probabilidades_ponderadas, 4)

    assert resultado.tolist() == pytest.approx([0.2])


def test_orden_pendiente_no_inventa_cantidad(tmp_path):
    db_path = tmp_path / "zenith.db"
    db.guardar_predicciones([{
        "producto": "Producto A",
        "cuadrante_kraljic": "Estratégico",
        "probabilidad": 0.8,
    }], 100.0, "2026-10-22", db_path)

    ordenes = db.obtener_ordenes(db_path)

    assert len(ordenes) == 1
    assert ordenes[0]["estado"] == "pendiente"
    assert ordenes[0]["cantidad_sugerida"] is None


def test_migra_ordenes_legacy_sin_conservar_cantidad_fija(tmp_path):
    db_path = tmp_path / "zenith.db"
    connection = db.get_connection(db_path)
    connection.execute("""
        CREATE TABLE ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT NOT NULL,
            cuadrante_kraljic TEXT NOT NULL,
            cantidad_sugerida INTEGER NOT NULL,
            probabilidad_desabasto REAL NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha_corte TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprobado_en TIMESTAMP
        )
    """)
    connection.execute("""
        INSERT INTO ordenes (producto, cuadrante_kraljic, cantidad_sugerida,
                             probabilidad_desabasto, fecha_corte)
        VALUES ('Producto A', 'Estratégico', 50, 0.8, '2026-10-22')
    """)
    connection.commit()
    connection.close()

    db.init_db(db_path)

    ordenes = db.obtener_ordenes(db_path)
    assert len(ordenes) == 1
    assert ordenes[0]["cantidad_sugerida"] is None


def test_evaluacion_usa_cortes_rodantes_y_quiebres_reales(monkeypatch):
    df = preparar_datos(predecir.CSV_PATH)
    productos = sorted(df["producto"].unique())

    def prediccion_sin_alertas(fecha_corte):
        return [
            {"producto": producto, "probabilidad": 0.0}
            for producto in productos
        ], 0.0

    monkeypatch.setattr(predecir, "predecir_lote", prediccion_sin_alertas)

    reporte = predecir.evaluar_ultimos_27_dias()

    assert reporte["origenes_evaluados"] == 21
    assert reporte["total_evaluados"] == 1050
    assert reporte["positivos_reales"] == 70
