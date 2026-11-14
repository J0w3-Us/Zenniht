"""Genera el dataset sintético de ZENIT para el prototipo (Actividad 3, Sección 1).

Universo cerrado: 1 farmacia ficticia, 50 productos, 90 días = 4,500 filas.
Salidas (se escriben junto a este script):
  - ventas.csv  -> archivo de carga del Hito de Entrada
  - zenith.db   -> base SQLite local (tabla `ventas`)

Reproducible: semilla fija. No usa internet ni paquetes de pago.
Uso:  python data/generar_datos.py
"""
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np

SEED = 42
DIAS = 90
FIN = date(2026, 11, 12)
INICIO = FIN - timedelta(days=DIAS - 1)
COLUMNAS = ["producto", "fecha", "unidades_vendidas", "existencia",
            "cuadrante_kraljic", "requiere_refrigeracion",
            "fecha_caducidad", "temperatura"]

# (nombre, cuadrante, requiere_refrigeracion, demanda_media_diaria, estacional)
ESTRATEGICO, APALANCAMIENTO, CUELLO, NO_CRITICO = (
    "Estratégico", "Apalancamiento", "Cuello de botella", "No crítico")
CATALOGO = [
    # 10 estratégicos: tratamientos crónicos y de patente
    ("Insulina glargina", ESTRATEGICO, 1, 8, False),
    ("Insulina NPH", ESTRATEGICO, 1, 6, False),
    ("Losartán 50 mg", ESTRATEGICO, 0, 14, False),
    ("Enalapril 10 mg", ESTRATEGICO, 0, 12, False),
    ("Amlodipino 5 mg", ESTRATEGICO, 0, 11, False),
    ("Atorvastatina 20 mg", ESTRATEGICO, 0, 10, False),
    ("Levotiroxina 100 mcg", ESTRATEGICO, 0, 9, False),
    ("Metformina 850 mg", ESTRATEGICO, 0, 15, False),
    ("Glibenclamida 5 mg", ESTRATEGICO, 0, 8, False),
    ("Salbutamol inhalador", ESTRATEGICO, 0, 7, False),
    # 15 de apalancamiento: genéricos de alta rotación
    ("Paracetamol 500 mg", APALANCAMIENTO, 0, 40, False),
    ("Ibuprofeno 400 mg", APALANCAMIENTO, 0, 30, False),
    ("Naproxeno 250 mg", APALANCAMIENTO, 0, 20, False),
    ("Omeprazol 20 mg", APALANCAMIENTO, 0, 25, False),
    ("Loratadina 10 mg", APALANCAMIENTO, 0, 18, False),
    ("Ambroxol jarabe", APALANCAMIENTO, 0, 14, False),
    ("Diclofenaco 50 mg", APALANCAMIENTO, 0, 17, False),
    ("Amoxicilina 500 mg", APALANCAMIENTO, 0, 16, False),
    ("Metamizol 500 mg", APALANCAMIENTO, 0, 19, False),
    ("Butilhioscina 10 mg", APALANCAMIENTO, 0, 13, False),
    ("Clorfenamina 4 mg", APALANCAMIENTO, 0, 12, False),
    ("Dimenhidrinato 50 mg", APALANCAMIENTO, 0, 10, False),
    ("Complejo B", APALANCAMIENTO, 0, 11, False),
    ("Vitamina C 500 mg", APALANCAMIENTO, 0, 15, False),
    ("Loperamida 2 mg", APALANCAMIENTO, 0, 9, False),
    # 10 cuello de botella: insumos de temporada (influenza)
    ("Vacuna influenza", CUELLO, 1, 4, True),
    ("Vacuna hepatitis B", CUELLO, 1, 2, True),
    ("Oseltamivir 75 mg", CUELLO, 0, 3, True),
    ("Antigripal sobres", CUELLO, 0, 12, True),
    ("Jarabe tos infantil", CUELLO, 0, 8, True),
    ("Descongestionante nasal", CUELLO, 0, 7, True),
    ("Suero oral", CUELLO, 0, 9, True),
    ("Pastillas para garganta", CUELLO, 0, 10, True),
    ("Vapor mentolado", CUELLO, 0, 6, True),
    ("Antihistamínico pediátrico", CUELLO, 0, 5, True),
    # 15 no críticos: insumos básicos
    ("Gasas estériles", NO_CRITICO, 0, 12, False),
    ("Alcohol 70%", NO_CRITICO, 0, 15, False),
    ("Algodón", NO_CRITICO, 0, 9, False),
    ("Curitas", NO_CRITICO, 0, 14, False),
    ("Cubrebocas", NO_CRITICO, 0, 16, False),
    ("Guantes de látex", NO_CRITICO, 0, 8, False),
    ("Jeringa 5 ml", NO_CRITICO, 0, 7, False),
    ("Termómetro digital", NO_CRITICO, 0, 3, False),
    ("Agua oxigenada", NO_CRITICO, 0, 8, False),
    ("Micropore", NO_CRITICO, 0, 6, False),
    ("Venda elástica", NO_CRITICO, 0, 5, False),
    ("Yodopovidona", NO_CRITICO, 0, 6, False),
    ("Pañuelos desechables", NO_CRITICO, 0, 10, False),
    ("Gel antibacterial", NO_CRITICO, 0, 13, False),
    ("Crema para pañal", NO_CRITICO, 0, 5, False),
]

# Interrupciones de surtido: el distribuidor no entrega durante las ventanas (día_inicio, día_fin).
# Cada producto tiene una ventana temprana (entrenamiento) y una tardía (últimos 30 días, prueba),
# así el modelo ve casos de quiebre al entrenar y también al evaluarse.
QUIEBRES = {
    "Insulina glargina": [(18, 26), (58, 66)],
    "Losartán 50 mg": [(22, 30), (60, 68)],
    "Vacuna influenza": [(26, 34), (62, 70)],
    "Paracetamol 500 mg": [(30, 38), (64, 72)],
    "Antigripal sobres": [(34, 42), (66, 74)],
    "Oseltamivir 75 mg": [(14, 22), (57, 64)],
    "Alcohol 70%": [(38, 46), (68, 76)],
}


def generar():
    assert len(CATALOGO) == 50, "El universo debe ser de 50 productos"
    rng = np.random.default_rng(SEED)
    fechas = [INICIO + timedelta(days=i) for i in range(DIAS)]
    temp = [round(31 - 5 * i / (DIAS - 1) + rng.normal(0, 1.2), 1) for i in range(DIAS)]
    ciclo_semanal = [1.0, 0.95, 0.95, 1.0, 1.1, 1.2, 1.1]  # lunes a domingo

    filas = []
    for nombre, cuad, refrig, media, estacional in CATALOGO:
        dias_caducidad = 180 if refrig else int(rng.integers(300, 900))
        caducidad = (FIN + timedelta(days=dias_caducidad)).isoformat()
        # Nivel al que se repone el stock (en insumos de temporada se calcula con el pico esperado).
        objetivo = int(media * (25 if estacional else 10)) + 10
        offset = int(rng.integers(0, 7))    # día de la semana en que llega el surtido
        existencia = objetivo
        ventanas = QUIEBRES.get(nombre, [])
        for i, f in enumerate(fechas):
            if i % 7 == offset and i > 0:
                if not any(lo <= i <= hi for lo, hi in ventanas):
                    existencia = objetivo
            lam = media * ciclo_semanal[f.weekday()]
            if f.day in (1, 15, 16, 30):                      # efecto de quincena
                lam *= 1.2
            if estacional:                                    # temporada de influenza
                lam *= (0.6 + 1.6 * i / (DIAS - 1)) * (1 + 0.04 * max(0.0, 31 - temp[i]))
            demanda = int(rng.poisson(lam))
            vendidas = min(demanda, existencia)
            existencia -= vendidas
            filas.append((nombre, f.isoformat(), vendidas, existencia, cuad,
                          refrig, caducidad, temp[i]))
    return filas


def guardar(filas, carpeta):
    csv_path = carpeta / "ventas.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNAS)
        w.writerows(filas)

    db_path = carpeta / "zenith.db"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE ventas (
        producto TEXT NOT NULL, fecha TEXT NOT NULL,
        unidades_vendidas INTEGER NOT NULL, existencia INTEGER NOT NULL,
        cuadrante_kraljic TEXT NOT NULL, requiere_refrigeracion INTEGER NOT NULL,
        fecha_caducidad TEXT NOT NULL, temperatura REAL NOT NULL,
        PRIMARY KEY (producto, fecha))""")
    con.executemany("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?)", filas)
    con.commit()
    con.close()
    return csv_path, db_path


if __name__ == "__main__":
    carpeta = Path(__file__).resolve().parent
    filas = generar()
    csv_path, db_path = guardar(filas, carpeta)
    quiebres = {f[0] for f in filas if f[3] == 0}
    print(f"Filas: {len(filas)} | Productos: {len({f[0] for f in filas})}")
    print(f"Productos con quiebre (existencia = 0): {len(quiebres)}")
    print(f"CSV: {csv_path}\nSQLite: {db_path}")
