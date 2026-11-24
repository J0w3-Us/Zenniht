"""Módulo de base de datos SQLite para ZENIT (Actividad 3).

Maneja las tablas locales:
  - ventas (4,500 filas de data/ventas.csv)
  - predicciones (probabilidad de desabasto a 7 días calculada por TFT)
  - ordenes (órdenes sugeridas con aprobación explícita del dueño)
"""
import csv
import json
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    conn = sqlite3.connect(path, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Crea las tablas requeridas si no existen."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predicciones_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto TEXT NOT NULL, fecha_corte TEXT NOT NULL,
                probabilidad REAL NOT NULL, modelo_version TEXT NOT NULL,
                dataset_sha256 TEXT NOT NULL, objetivo TEXT NOT NULL,
                tiempo_inferencia_ms REAL NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evaluaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporte_json TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id TEXT PRIMARY KEY,
                razon_social TEXT NOT NULL,
                rfc TEXT,
                plazo_pago_dias INTEGER DEFAULT 30,
                estatus_verificacion TEXT DEFAULT 'verificado',
                fuente_verificacion TEXT,
                vigencia_hasta TEXT,
                contacto_email TEXT,
                contacto_telefono TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bitacora (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento TEXT NOT NULL,
                entidad TEXT NOT NULL,
                entidad_id TEXT NOT NULL,
                usuario TEXT NOT NULL,
                detalle_json TEXT NOT NULL,
                fecha_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lotes (
                id TEXT PRIMARY KEY,
                producto TEXT NOT NULL,
                fecha_caducidad TEXT NOT NULL,
                cantidad_inicial INTEGER NOT NULL,
                cantidad_actual INTEGER NOT NULL,
                estado TEXT NOT NULL DEFAULT 'activo',
                ubicacion TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recepciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER,
                producto TEXT NOT NULL,
                lote_id TEXT NOT NULL,
                cantidad_recibida INTEGER NOT NULL,
                temperatura_recepcion REAL,
                comprobante_remision TEXT,
                sha256_remision TEXT,
                recibido_por TEXT NOT NULL,
                fecha_recepcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id),
                FOREIGN KEY (lote_id) REFERENCES lotes(id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lecturas_frio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_id TEXT NOT NULL,
                temperatura REAL NOT NULL,
                fecha_hora TEXT NOT NULL,
                en_rango INTEGER NOT NULL,
                registrado_por TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        columnas_ordenes = conn.execute("PRAGMA table_info(ordenes)").fetchall()
        cantidad_col = next((c for c in columnas_ordenes if c["name"] == "cantidad_sugerida"), None)
        if cantidad_col and cantidad_col["notnull"]:
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
                    aprobado_en TIMESTAMP,
                    motivo_descarte TEXT,
                    pospuesta_hasta TEXT,
                    proveedor_id TEXT,
                    cantidad_aprobada INTEGER,
                    total_centavos INTEGER,
                    usuario TEXT,
                    folio_emision TEXT,
                    emitido_en TIMESTAMP,
                    recibido_en TIMESTAMP
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
            columnas_ordenes = conn.execute("PRAGMA table_info(ordenes)").fetchall()

        nombres_cols = {c["name"] for c in columnas_ordenes}
        if "motivo_descarte" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN motivo_descarte TEXT;")
        if "pospuesta_hasta" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN pospuesta_hasta TEXT;")
        if "proveedor_id" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN proveedor_id TEXT;")
        if "cantidad_aprobada" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN cantidad_aprobada INTEGER;")
        if "total_centavos" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN total_centavos INTEGER;")
        if "usuario" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN usuario TEXT;")
        if "folio_emision" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN folio_emision TEXT;")
        if "emitido_en" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN emitido_en TIMESTAMP;")
        if "recibido_en" not in nombres_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN recibido_en TIMESTAMP;")
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
            INSERT INTO predicciones_historico (
                producto, fecha_corte, probabilidad, modelo_version,
                dataset_sha256, objetivo, tiempo_inferencia_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (p["producto"], fecha_corte, float(p["probabilidad"]),
             p.get("modelo_version", "legacy"), p.get("dataset_sha256", ""),
             p.get("objetivo", "diario_legacy"), tiempo_ms)
            for p in predicciones
        ])
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

        # Crear órdenes sugeridas pendientes para productos en desabasto con cantidad calculada
        for p in predicciones:
            if float(p["probabilidad"]) >= 0.50:
                existente = conn.execute(
                    "SELECT id FROM ordenes WHERE producto = ? AND fecha_corte = ?",
                    (p["producto"], fecha_corte)
                ).fetchone()
                if not existente:
                    # Calcular cantidad sugerida real basada en demanda, stock y lote mínimo
                    try:
                        from presupuesto import obtener_demanda_diaria_sin_quiebre
                        demanda_d = obtener_demanda_diaria_sin_quiebre(p["producto"], fecha_corte, db_path=db_path)
                        stock_actual_row = conn.execute(
                            "SELECT existencia FROM ventas WHERE producto = ? AND fecha = ?",
                            (p["producto"], fecha_corte)
                        ).fetchone()
                        stock_e = int(stock_actual_row["existencia"]) if stock_actual_row else 0
                        
                        lote_row = conn.execute(
                            "SELECT lote_minimo_compra FROM catalogo_precios WHERE producto = ?",
                            (p["producto"],)
                        ).fetchone()
                        lote_min = int(lote_row["lote_minimo_compra"]) if (lote_row and lote_row["lote_minimo_compra"]) else 5
                        
                        import math
                        necesidad = max(0.0, (demanda_d * 10) - stock_e)
                        cant_calc = max(1, int(math.ceil(necesidad / lote_min))) * lote_min if necesidad > 0 else lote_min
                    except Exception:
                        cant_calc = None

                    conn.execute("""
                        INSERT INTO ordenes (
                            producto, cuadrante_kraljic, cantidad_sugerida, probabilidad_desabasto,
                            fecha_corte, estado
                        ) VALUES (?, ?, ?, ?, ?, 'pendiente');
                    """, (
                        p["producto"],
                        p["cuadrante_kraljic"],
                        cant_calc,
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


def guardar_evaluacion(reporte, db_path=None):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("INSERT INTO evaluaciones (reporte_json) VALUES (?)", (json.dumps(reporte, ensure_ascii=False),))
    finally:
        conn.close()


def obtener_evaluacion(db_path=None):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        fila = conn.execute("SELECT reporte_json FROM evaluaciones ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(fila[0]) if fila else None
    finally:
        conn.close()


def obtener_ordenes(db_path: Optional[Path] = None) -> List[Dict[str, object]]:
    """Devuelve todas las órdenes sugeridas."""
    init_db(db_path)
    conn = get_connection(db_path)
    filas = conn.execute("SELECT * FROM ordenes ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(f) for f in filas]


PROVEEDORES_SEMILLA = [
    {
        "id": "PROV-FARMA-NAL-01",
        "razon_social": "Distribuidora Farmacéutica Nacional S.A. de C.V.",
        "rfc": "DFN980512AB3",
        "plazo_pago_dias": 30,
        "estatus_verificacion": "verificado",
        "fuente_verificacion": "Registro Público Sanitario / COFEPRIS",
        "vigencia_hasta": "2027-12-31",
        "contacto_email": "ventas@distfarmacloud.mx",
        "contacto_telefono": "+52 55 5482 1000",
    },
    {
        "id": "PROV-BIO-ESP-02",
        "razon_social": "Biológicos y Especialidades del Centro S.A. de C.V.",
        "rfc": "BEC041120XY1",
        "plazo_pago_dias": 15,
        "estatus_verificacion": "verificado",
        "fuente_verificacion": "Registro de Insumos Especializados",
        "vigencia_hasta": "2027-08-30",
        "contacto_email": "contacto@biologicoscentro.mx",
        "contacto_telefono": "+52 33 3615 2200",
    },
    {
        "id": "PROV-GEN-PACIFICO-03",
        "razon_social": "Genéricos y Materiales del Pacífico S. de R.L.",
        "rfc": "GMP100315LK8",
        "plazo_pago_dias": 45,
        "estatus_verificacion": "verificado",
        "fuente_verificacion": "Padrón Estatal de Proveedores",
        "vigencia_hasta": "2026-12-31",
        "contacto_email": "pedidos@genericosypacifico.com",
        "contacto_telefono": "+52 66 4684 9010",
    },
]


def sembrar_proveedores(db_path: Optional[Path] = None) -> int:
    """Siembra proveedores verificados iniciales si la tabla está vacía."""
    init_db(db_path)
    conn = get_connection(db_path)
    conteo = conn.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
    if conteo > 0:
        conn.close()
        return conteo

    with conn:
        for p in PROVEEDORES_SEMILLA:
            conn.execute("""
                INSERT OR REPLACE INTO proveedores (
                    id, razon_social, rfc, plazo_pago_dias, estatus_verificacion,
                    fuente_verificacion, vigencia_hasta, contacto_email, contacto_telefono
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                p["id"],
                p["razon_social"],
                p["rfc"],
                p["plazo_pago_dias"],
                p["estatus_verificacion"],
                p["fuente_verificacion"],
                p["vigencia_hasta"],
                p["contacto_email"],
                p["contacto_telefono"],
            ))
    conn.close()
    return len(PROVEEDORES_SEMILLA)


def registrar_bitacora(
    evento: str,
    entidad: str,
    entidad_id: str,
    usuario: str,
    detalle: Dict[str, Any],
    db_path: Optional[Path] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Registra un evento de auditoría inmutable en bitacora con marca UTC ISO 8601."""
    import json
    consulta = """
        INSERT INTO bitacora (evento, entidad, entidad_id, usuario, detalle_json)
        VALUES (?, ?, ?, ?, ?);
    """
    valores = (evento, entidad, str(entidad_id), usuario, json.dumps(detalle, ensure_ascii=False))

    if conn is not None:
        conn.execute(consulta, valores)
        return

    init_db(db_path)
    conexion = get_connection(db_path)
    with conexion:
        conexion.execute(consulta, valores)
    conexion.close()


def obtener_proveedores(db_path: Optional[Path] = None) -> List[Dict[str, object]]:
    """Devuelve los proveedores registrados."""
    init_db(db_path)
    sembrar_proveedores(db_path)
    conn = get_connection(db_path)
    filas = conn.execute("SELECT * FROM proveedores ORDER BY razon_social ASC").fetchall()
    conn.close()
    return [dict(f) for f in filas]


def aprobar_orden(
    orden_id: int,
    db_path: Optional[Path] = None,
    cantidad: Optional[int] = None,
    usuario: str = "encargado_farmacia",
) -> bool:
    """Aprueba una orden sugerida (transición pendiente -> aprobada)."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden or orden["estado"] != "pendiente":
                return False

            cant_aprobada = cantidad if (cantidad is not None and cantidad > 0) else orden["cantidad_sugerida"]
            res = conn.execute("""
                UPDATE ordenes
                SET estado = 'aprobada',
                    cantidad_aprobada = ?,
                    usuario = ?,
                    aprobado_en = CURRENT_TIMESTAMP
                WHERE id = ? AND estado = 'pendiente';
            """, (cant_aprobada, usuario, orden_id))
            afectados = res.rowcount
            if afectados > 0:
                registrar_bitacora(
                    evento="ORDEN_APROBADA",
                    entidad="ordenes",
                    entidad_id=str(orden_id),
                    usuario=usuario,
                    detalle={"cantidad_aprobada": cant_aprobada, "producto": orden["producto"]},
                    conn=conn,
                )
            return afectados > 0
    finally:
        conn.close()


def descartar_orden(
    orden_id: int,
    motivo: str,
    db_path: Optional[Path] = None,
    usuario: str = "encargado_farmacia",
) -> bool:
    """Descarta una orden sugerida con motivo obligatorio (pendiente -> descartada)."""
    if not motivo or not motivo.strip():
        raise ValueError("El motivo de descarte es obligatorio.")

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden or orden["estado"] != "pendiente":
                return False

            res = conn.execute("""
                UPDATE ordenes
                SET estado = 'descartada',
                    motivo_descarte = ?,
                    usuario = ?
                WHERE id = ? AND estado = 'pendiente';
            """, (motivo.strip(), usuario, orden_id))
            afectados = res.rowcount
            if afectados > 0:
                registrar_bitacora(
                    evento="ORDEN_DESCARTADA",
                    entidad="ordenes",
                    entidad_id=str(orden_id),
                    usuario=usuario,
                    detalle={"motivo": motivo.strip(), "producto": orden["producto"]},
                    conn=conn,
                )
            return afectados > 0
    finally:
        conn.close()


def posponer_orden(
    orden_id: int,
    fecha_hasta: str,
    db_path: Optional[Path] = None,
    usuario: str = "encargado_farmacia",
) -> bool:
    """Pospone una orden pendiente hasta una fecha determinada (pendiente -> pospuesta)."""
    if not fecha_hasta or not fecha_hasta.strip():
        raise ValueError("La fecha pospuesta es obligatoria (YYYY-MM-DD).")

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden or orden["estado"] != "pendiente":
                return False

            res = conn.execute("""
                UPDATE ordenes
                SET estado = 'pospuesta',
                    pospuesta_hasta = ?,
                    usuario = ?
                WHERE id = ? AND estado = 'pendiente';
            """, (fecha_hasta.strip(), usuario, orden_id))
            afectados = res.rowcount
            if afectados > 0:
                registrar_bitacora(
                    evento="ORDEN_POSPUESTA",
                    entidad="ordenes",
                    entidad_id=str(orden_id),
                    usuario=usuario,
                    detalle={"pospuesta_hasta": fecha_hasta.strip(), "producto": orden["producto"]},
                    conn=conn,
                )
            return afectados > 0
    finally:
        conn.close()


def emitir_orden(
    orden_id: int,
    proveedor_id: Optional[str] = None,
    db_path: Optional[Path] = None,
    usuario: str = "encargado_farmacia",
) -> Dict[str, Any]:
    """Emite formalmente una orden previamente aprobada (aprobada -> emitida)."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                raise ValueError(f"Orden no encontrada: {orden_id}")
            if orden["estado"] != "aprobada":
                raise ValueError(f"Solo se pueden emitir órdenes en estado 'aprobada'. Estado actual: '{orden['estado']}'")

            folio = f"ORD-ZENIT-{orden_id:04d}"
            prov = proveedor_id or orden["proveedor_id"] or "PROV-FARMA-NAL-01"

            conn.execute("""
                UPDATE ordenes
                SET estado = 'emitida',
                    folio_emision = ?,
                    proveedor_id = ?,
                    emitido_en = CURRENT_TIMESTAMP
                WHERE id = ? AND estado = 'aprobada';
            """, (folio, prov, orden_id))

            orden_actualizada = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            return dict(orden_actualizada)
    finally:
        conn.close()


def registrar_recepcion_mercancia(
    orden_id: Optional[int],
    producto: str,
    lote_id: str,
    cantidad_recibida: int,
    fecha_caducidad: str,
    temperatura_recepcion: Optional[float] = None,
    ubicacion: Optional[str] = None,
    comprobante_remision: Optional[str] = None,
    sha256_remision: Optional[str] = None,
    recibido_por: str = "almacenista_farmacia",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Registra físicamente una recepción de mercancía, crea/actualiza el lote y valida cadena de frío."""
    if cantidad_recibida <= 0:
        raise ValueError("La cantidad recibida debe ser mayor a 0.")
    if not lote_id or not lote_id.strip():
        raise ValueError("El código de lote es obligatorio.")
    if not fecha_caducidad or not fecha_caducidad.strip():
        raise ValueError("La fecha de caducidad es obligatoria (YYYY-MM-DD).")

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            # Consultar si el producto requiere refrigeración
            prod_info = conn.execute(
                "SELECT requiere_refrigeracion FROM ventas WHERE producto = ? LIMIT 1",
                (producto,)
            ).fetchone()
            req_frio = bool(prod_info["requiere_refrigeracion"]) if prod_info else False

            estado_lote = "activo"
            excursion_termica = False
            if req_frio:
                if temperatura_recepcion is None:
                    estado_lote = "cuarentena"
                    excursion_termica = True
                elif temperatura_recepcion < 2.0 or temperatura_recepcion > 8.0:
                    estado_lote = "cuarentena"
                    excursion_termica = True

            # Registrar en tabla lotes
            lote_existente = conn.execute("SELECT id, cantidad_actual FROM lotes WHERE id = ?", (lote_id,)).fetchone()
            if lote_existente:
                nueva_cant = lote_existente["cantidad_actual"] + cantidad_recibida
                conn.execute(
                    "UPDATE lotes SET cantidad_actual = ?, estado = ? WHERE id = ?",
                    (nueva_cant, estado_lote, lote_id)
                )
            else:
                conn.execute("""
                    INSERT INTO lotes (id, producto, fecha_caducidad, cantidad_inicial, cantidad_actual, estado, ubicacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (lote_id, producto, fecha_caducidad, cantidad_recibida, cantidad_recibida, estado_lote, ubicacion))

            # Registrar en tabla recepciones
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO recepciones (
                    orden_id, producto, lote_id, cantidad_recibida, temperatura_recepcion,
                    comprobante_remision, sha256_remision, recibido_por
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (orden_id, producto, lote_id, cantidad_recibida, temperatura_recepcion, comprobante_remision, sha256_remision, recibido_por))
            recepcion_id = cur.lastrowid

            # Si viene asociada a una orden, actualizar estado de la orden
            if orden_id:
                orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
                if orden and orden["estado"] in ("emitida", "recibida_parcial"):
                    cant_esperada = int(orden["cantidad_aprobada"] or orden["cantidad_sugerida"] or 0)
                    nuevo_estado = "recibida" if cantidad_recibida >= cant_esperada else "recibida_parcial"
                    conn.execute("UPDATE ordenes SET estado = ?, recibido_en = CURRENT_TIMESTAMP WHERE id = ?", (nuevo_estado, orden_id))

            # Bitácora
            evento_bitacora = "RECEPCION_CUARENTENA_FRIO" if excursion_termica else "RECEPCION_MERCANCIA"
            registrar_bitacora(
                evento=evento_bitacora,
                entidad="recepciones",
                entidad_id=str(recepcion_id),
                usuario=recibido_por,
                detalle={
                    "producto": producto,
                    "lote_id": lote_id,
                    "cantidad": cantidad_recibida,
                    "temperatura": temperatura_recepcion,
                    "estado_lote": estado_lote,
                    "excursion_termica": excursion_termica,
                },
                conn=conn,
            )

            res = conn.execute("SELECT * FROM recepciones WHERE id = ?", (recepcion_id,)).fetchone()
            dict_res = dict(res)
            dict_res["estado_lote"] = estado_lote
            dict_res["excursion_termica"] = excursion_termica
            return dict_res
    finally:
        conn.close()


def registrar_lectura_frio(
    equipo_id: str,
    temperatura: float,
    registrado_por: str = "operador_frio",
    fecha_hora: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Registra una lectura de temperatura en equipos de cadena de frío (2.0°C a 8.0°C)."""
    import datetime
    ahora_utc = fecha_hora or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    en_rango = 1 if (2.0 <= temperatura <= 8.0) else 0

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO lecturas_frio (equipo_id, temperatura, fecha_hora, en_rango, registrado_por)
                VALUES (?, ?, ?, ?, ?);
            """, (equipo_id, temperatura, ahora_utc, en_rango, registrado_por))
            lectura_id = cur.lastrowid

            if not en_rango:
                registrar_bitacora(
                    evento="EXCURSION_TERMICA_CADENA_FRIO",
                    entidad="lecturas_frio",
                    entidad_id=str(lectura_id),
                    usuario=registrado_por,
                    detalle={"equipo_id": equipo_id, "temperatura": temperatura, "alerta": "Fuera del rango 2°C - 8°C"},
                    conn=conn,
                )

            fila = conn.execute("SELECT * FROM lecturas_frio WHERE id = ?", (lectura_id,)).fetchone()
            return dict(fila)
    finally:
        conn.close()


def obtener_alertas_caducidad(
    dias_limite: int = 90,
    fecha_referencia: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Devuelve lotes activos ordenados por FEFO (First Expired, First Out) próximos a vencer."""
    import datetime
    if not fecha_referencia:
        fecha_ref = datetime.date.today().isoformat()
    else:
        fecha_ref = fecha_referencia

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        # Calcular fecha límite
        ref_dt = datetime.date.fromisoformat(fecha_ref)
        fecha_max = (ref_dt + datetime.timedelta(days=dias_limite)).isoformat()

        filas = conn.execute("""
            SELECT l.id as lote_id, l.producto, l.fecha_caducidad, l.cantidad_actual,
                   l.estado, l.ubicacion, cp.precio_compra_unitario
            FROM lotes l
            LEFT JOIN catalogo_precios cp ON l.producto = cp.producto
            WHERE l.estado = 'activo' AND l.cantidad_actual > 0
              AND l.fecha_caducidad <= ?
            ORDER BY l.fecha_caducidad ASC
        """, (fecha_max,)).fetchall()

        resultado = []
        for f in filas:
            f_cad = datetime.date.fromisoformat(f["fecha_caducidad"])
            dias_restantes = (f_cad - ref_dt).days
            precio_unit = float(f["precio_compra_unitario"] or 0.0)
            valor_en_riesgo = round(f["cantidad_actual"] * precio_unit, 2)
            resultado.append({
                "lote_id": f["lote_id"],
                "producto": f["producto"],
                "fecha_caducidad": f["fecha_caducidad"],
                "dias_restantes": dias_restantes,
                "vencido": dias_restantes < 0,
                "cantidad_actual": f["cantidad_actual"],
                "ubicacion": f["ubicacion"],
                "valor_en_riesgo_mxn": valor_en_riesgo,
            })
        return resultado
    finally:
        conn.close()


def obtener_lecturas_frio_recientes(
    equipo_id: Optional[str] = None,
    limite: int = 20,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Consulta las lecturas térmicas registradas."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        if equipo_id:
            filas = conn.execute(
                "SELECT * FROM lecturas_frio WHERE equipo_id = ? ORDER BY id DESC LIMIT ?",
                (equipo_id, limite)
            ).fetchall()
        else:
            filas = conn.execute(
                "SELECT * FROM lecturas_frio ORDER BY id DESC LIMIT ?",
                (limite,)
            ).fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()



def recibir_orden(
    orden_id: int,
    cantidad_recibida: int,
    db_path: Optional[Path] = None,
    usuario: str = "almacenista_farmacia",
) -> Dict[str, Any]:
    """Registra la recepción física de una orden emitida (emitida -> recibida o recibida_parcial)."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            orden = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            if not orden:
                raise ValueError(f"Orden no encontrada: {orden_id}")
            if orden["estado"] not in ("emitida", "recibida_parcial"):
                raise ValueError(f"Solo se pueden recibir órdenes en estado 'emitida' o 'recibida_parcial'.")

            cant_esperada = int(orden["cantidad_aprobada"] or orden["cantidad_sugerida"] or 0)
            nuevo_estado = "recibida" if cantidad_recibida >= cant_esperada else "recibida_parcial"

            conn.execute("""
                UPDATE ordenes
                SET estado = ?,
                    recibido_en = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (nuevo_estado, orden_id))

            registrar_bitacora(
                evento=f"ORDEN_{nuevo_estado.upper()}",
                entidad="ordenes",
                entidad_id=str(orden_id),
                usuario=usuario,
                detalle={"cantidad_recibida": cantidad_recibida, "esperada": cant_esperada},
                conn=conn,
            )

            orden_actualizada = conn.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
            return dict(orden_actualizada)
    finally:
        conn.close()




