"""Módulo de base de datos SQLite para ZENIT (Actividad 3).

Maneja las tablas locales:
  - ventas (4,500 filas de data/ventas.csv)
  - predicciones (probabilidad de desabasto a 7 días calculada por TFT)
  - ordenes (órdenes sugeridas con aprobación explícita del dueño)
"""
import csv
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Los datos locales de ZENIT se mantienen en el directorio data/ de la raíz.
_CURRENT_DIR = Path(__file__).resolve().parent
DATA_DIR = _CURRENT_DIR / "data"
DB_PATH = Path(os.environ.get("ZENIT_DB_PATH", DATA_DIR / "zenith.db"))
CSV_PATH = Path(os.environ.get("ZENIT_CSV_PATH", DATA_DIR / "ventas.csv"))

COLUMNAS_VENTAS = [
    "producto",
    "fecha",
    "unidades_vendidas",
    "existencia",
    "cuadrante_kraljic",
    "requiere_refrigeracion",
    "fecha_caducidad",
    "temperatura",
]
CUADRANTES_ESPERADOS = {
    "Estratégico": 10,
    "Apalancamiento": 15,
    "Cuello de botella": 10,
    "No crítico": 15,
}


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Obtiene una conexión con row_factory Row para fácil mapeo."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Crea las tablas requeridas si no existen."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                producto TEXT NOT NULL,
                fecha TEXT NOT NULL,
                unidades_vendidas INTEGER NOT NULL,
                existencia INTEGER NOT NULL,
                cuadrante_kraljic TEXT NOT NULL,
                requiere_refrigeracion INTEGER NOT NULL,
                fecha_caducidad TEXT NOT NULL,
                temperatura REAL NOT NULL,
                PRIMARY KEY (producto, fecha)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predicciones (
                producto TEXT PRIMARY KEY,
                probabilidad REAL NOT NULL,
                en_desabasto INTEGER NOT NULL,
                cuadrante_kraljic TEXT NOT NULL,
                fecha_corte TEXT NOT NULL,
                tiempo_inferencia_ms REAL NOT NULL,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto TEXT NOT NULL,
                cuadrante_kraljic TEXT NOT NULL,
                cantidad_sugerida INTEGER,
                probabilidad_desabasto REAL NOT NULL,
                estado TEXT NOT NULL DEFAULT 'pendiente',
                fecha_corte TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                aprobado_en TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS catalogo_precios (
                producto TEXT PRIMARY KEY,
                precio_compra_centavos INTEGER NOT NULL,
                tasa_iva_pct REAL NOT NULL DEFAULT 16.0,
                lote_minimo INTEGER NOT NULL DEFAULT 1,
                banda_min_centavos INTEGER,
                banda_max_centavos INTEGER,
                vigencia_desde TEXT,
                vigencia_hasta TEXT,
                proveedor_id TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS presupuestos_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_corte TEXT NOT NULL,
                techo_centavos INTEGER,
                subtotal_centavos INTEGER NOT NULL,
                iva_centavos INTEGER NOT NULL,
                total_centavos INTEGER NOT NULL,
                faltante_centavos INTEGER DEFAULT 0,
                lineas_json TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        columnas_ordenes = conn.execute("PRAGMA table_info(ordenes)").fetchall()
        cantidad = next(c for c in columnas_ordenes if c["name"] == "cantidad_sugerida")
        if cantidad["notnull"]:
            conn.execute("ALTER TABLE ordenes RENAME TO ordenes_anteriores")
            conn.execute("""
                CREATE TABLE ordenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT NOT NULL,
                    cuadrante_kraljic TEXT NOT NULL,
                    cantidad_sugerida INTEGER,
                    probabilidad_desabasto REAL NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'pendiente',
                    fecha_corte TEXT NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    aprobado_en TIMESTAMP
                );
            """)
            conn.execute("""
                INSERT INTO ordenes (
                    id, producto, cuadrante_kraljic, cantidad_sugerida,
                    probabilidad_desabasto, estado, fecha_corte, creado_en, aprobado_en
                )
                SELECT id, producto, cuadrante_kraljic, NULL,
                       probabilidad_desabasto, estado, fecha_corte, creado_en, aprobado_en
                FROM ordenes_anteriores;
            """)
            conn.execute("DROP TABLE ordenes_anteriores")
    conn.close()


def cargar_csv(csv_path: Optional[Path] = None, db_path: Optional[Path] = None) -> Dict[str, object]:
    """Carga y valida el archivo CSV en SQLite.
    
    Hito de Entrada:
      - 4,500 registros
      - 50 productos
      - 90 días
      - Distribución Kraljic: Estratégico (10), Apalancamiento (15), Cuello (10), No crítico (15)
      - Cero nulos y 8 columnas exactas
    """
    path_csv = csv_path or CSV_PATH
    init_db(db_path)
    conn = get_connection(db_path)

    if not path_csv.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path_csv}")

    with open(path_csv, mode="r", encoding="utf-8", newline="") as fh:
        lector = csv.DictReader(fh)
        if lector.fieldnames != COLUMNAS_VENTAS:
            raise ValueError(f"Columnas inválidas en CSV. Esperadas: {COLUMNAS_VENTAS}")

        filas = list(lector)

    # Validaciones binarias del hito de entrada
    total_filas = len(filas)
    productos = {f["producto"] for f in filas}
    fechas = {f["fecha"] for f in filas}

    for f in filas:
        if any(v is None or not v.strip() for v in f.values()):
            raise ValueError("El CSV contiene valores nulos o vacíos.")

    if total_filas != 4500:
        raise ValueError(f"Se esperaban 4,500 filas y se encontraron {total_filas}.")
    if len(productos) != 50:
        raise ValueError(f"Se esperaban 50 productos y se encontraron {len(productos)}.")
    if len(fechas) != 90:
        raise ValueError(f"Se esperaban 90 fechas y se encontraron {len(fechas)}.")

    filas_por_producto = Counter(f["producto"] for f in filas)
    productos_por_fecha = Counter(f["fecha"] for f in filas)
    fechas_por_producto = defaultdict(set)
    cuadrante_por_producto = {}
    for fila in filas:
        fechas_por_producto[fila["producto"]].add(fila["fecha"])
        cuadrante = fila["cuadrante_kraljic"]
        producto = fila["producto"]
        if producto in cuadrante_por_producto and cuadrante_por_producto[producto] != cuadrante:
            raise ValueError(f"El cuadrante Kraljic no es consistente para {producto}.")
        cuadrante_por_producto[producto] = cuadrante

    if any(conteo != 90 for conteo in filas_por_producto.values()):
        raise ValueError("Cada producto debe tener exactamente 90 registros.")
    if any(conteo != 50 for conteo in productos_por_fecha.values()):
        raise ValueError("Cada fecha debe contener exactamente 50 productos.")
    if any(fechas_producto != fechas for fechas_producto in fechas_por_producto.values()):
        raise ValueError("Todos los productos deben cubrir las mismas 90 fechas.")

    distribucion = Counter(cuadrante_por_producto.values())
    if dict(distribucion) != CUADRANTES_ESPERADOS:
        raise ValueError(
            "La distribución Kraljic debe ser: Estratégico 10, "
            "Apalancamiento 15, Cuello de botella 10 y No crítico 15."
        )

    with conn:
        conn.execute("DELETE FROM ventas;")
        conn.executemany("""
            INSERT INTO ventas (
                producto, fecha, unidades_vendidas, existencia,
                cuadrante_kraljic, requiere_refrigeracion, fecha_caducidad, temperatura
            ) VALUES (
                :producto, :fecha, :unidades_vendidas, :existencia,
                :cuadrante_kraljic, :requiere_refrigeracion, :fecha_caducidad, :temperatura
            );
        """, filas)

    conteo = conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
    conn.close()

    return {
        "status": "success",
        "mensaje": f"{conteo} registros cargados correctamente ({len(productos)} productos, {len(fechas)} días)",
        "filas": conteo,
        "productos": len(productos),
        "fechas": len(fechas),
    }


def guardar_predicciones(
    predicciones: List[Dict[str, object]],
    tiempo_ms: float,
    fecha_corte: str,
    db_path: Optional[Path] = None
) -> None:
    """Guarda predicciones de desabasto generadas por el TFT."""
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM predicciones;")
        conn.executemany("""
            INSERT OR REPLACE INTO predicciones (
                producto, probabilidad, en_desabasto, cuadrante_kraljic,
                fecha_corte, tiempo_inferencia_ms
            ) VALUES (?, ?, ?, ?, ?, ?);
        """, [
            (
                p["producto"],
                float(p["probabilidad"]),
                1 if float(p["probabilidad"]) >= 0.50 else 0,
                p["cuadrante_kraljic"],
                fecha_corte,
                tiempo_ms
            )
            for p in predicciones
        ])

        # Crear órdenes sugeridas pendientes para productos en desabasto
        for p in predicciones:
            if float(p["probabilidad"]) >= 0.50:
                existente = conn.execute(
                    "SELECT id FROM ordenes WHERE producto = ? AND fecha_corte = ? AND estado = 'pendiente'",
                    (p["producto"], fecha_corte)
                ).fetchone()
                if not existente:
                    conn.execute("""
                        INSERT INTO ordenes (
                            producto, cuadrante_kraljic, probabilidad_desabasto,
                            fecha_corte, estado
                        ) VALUES (?, ?, ?, ?, 'pendiente');
                    """, (
                        p["producto"],
                        p["cuadrante_kraljic"],
                        float(p["probabilidad"]),
                        fecha_corte
                    ))
    conn.close()


def obtener_predicciones(db_path: Optional[Path] = None) -> List[Dict[str, object]]:
    """Devuelve las predicciones actuales."""
    init_db(db_path)
    conn = get_connection(db_path)
    filas = conn.execute("SELECT * FROM predicciones").fetchall()
    conn.close()
    return [dict(f) for f in filas]


def obtener_ordenes(db_path: Optional[Path] = None) -> List[Dict[str, object]]:
    """Devuelve todas las órdenes sugeridas."""
    init_db(db_path)
    conn = get_connection(db_path)
    filas = conn.execute("SELECT * FROM ordenes ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(f) for f in filas]


def aprobar_orden(orden_id: int, db_path: Optional[Path] = None) -> bool:
    """Aprueba una orden sugerida (aprobación humana explícita)."""
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        res = conn.execute("""
            UPDATE ordenes
            SET estado = 'aprobada', aprobado_en = CURRENT_TIMESTAMP
            WHERE id = ? AND estado = 'pendiente';
        """, (orden_id,))
        afectados = res.rowcount
    conn.close()
    return afectados > 0

