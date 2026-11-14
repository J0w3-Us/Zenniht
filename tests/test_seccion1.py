"""Pruebas que convierten las restricciones de la Sección 1 en verificaciones automáticas.
Ejecutar: python data/generar_datos.py && pytest -q
"""
import csv
import sqlite3
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
COLUMNAS = ["producto", "fecha", "unidades_vendidas", "existencia",
            "cuadrante_kraljic", "requiere_refrigeracion",
            "fecha_caducidad", "temperatura"]


def leer():
    with open(DATA / "ventas.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_columnas_exactas():
    with open(DATA / "ventas.csv", encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == COLUMNAS


def test_universo_cerrado():
    filas = leer()
    assert len(filas) == 4500
    assert len({f["producto"] for f in filas}) == 50
    assert len({f["fecha"] for f in filas}) == 90


def test_distribucion_kraljic():
    por_prod = {f["producto"]: f["cuadrante_kraljic"] for f in leer()}
    assert Counter(por_prod.values()) == {
        "Estratégico": 10, "Apalancamiento": 15, "Cuello de botella": 10, "No crítico": 15}


def test_sin_nulos():
    assert all(all(v not in ("", None) for v in f.values()) for f in leer())


def test_al_menos_5_productos_con_quiebre_en_los_ultimos_27_dias():
    filas = leer()
    fechas = sorted({f["fecha"] for f in filas})
    prueba = set(fechas[-27:])
    con_quiebre = {f["producto"] for f in filas
                   if f["fecha"] in prueba and int(f["existencia"]) == 0}
    assert len(con_quiebre) >= 5


def test_sqlite_coincide_con_el_csv():
    con = sqlite3.connect(DATA / "zenith.db")
    assert con.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 4500
    con.close()
