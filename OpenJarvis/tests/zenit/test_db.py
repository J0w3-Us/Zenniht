import csv

import pytest

import db


def test_cargar_csv_acepta_el_dataset_cerrado(tmp_path):
    ruta_db = tmp_path / "zenith.db"

    resultado = db.cargar_csv(db.CSV_PATH, ruta_db)

    assert resultado["filas"] == 4500
    assert resultado["productos"] == 50
    assert resultado["fechas"] == 90
    conn = db.get_connection(ruta_db)
    assert conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 4500
    conn.close()


def test_cargar_csv_rechaza_universo_incompleto_sin_borrar_datos(tmp_path):
    ruta_db = tmp_path / "zenith.db"
    db.cargar_csv(db.CSV_PATH, ruta_db)
    csv_incompleto = tmp_path / "incompleto.csv"

    with db.CSV_PATH.open(encoding="utf-8", newline="") as origen:
        fila = next(csv.DictReader(origen))
    with csv_incompleto.open("w", encoding="utf-8", newline="") as destino:
        escritor = csv.DictWriter(destino, fieldnames=db.COLUMNAS_VENTAS)
        escritor.writeheader()
        escritor.writerow(fila)

    with pytest.raises(ValueError, match="4,500 filas"):
        db.cargar_csv(csv_incompleto, ruta_db)

    conn = db.get_connection(ruta_db)
    assert conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 4500
    conn.close()
