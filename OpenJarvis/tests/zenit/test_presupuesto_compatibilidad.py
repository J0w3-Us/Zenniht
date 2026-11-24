"""El motor usa las columnas reales de SQLite, sin asumir precios externos."""
import db
from presupuesto import calcular_presupuesto


def test_presupuesto_lee_centavos_lotes_e_iva_del_catalogo(tmp_path):
    ruta = tmp_path / "cotizacion.db"
    db.cargar_csv(db.CSV_PATH, ruta)
    db.guardar_predicciones([{"producto": "Insulina glargina", "cuadrante_kraljic": "Estratégico", "probabilidad": .9}],
        20., "2026-10-22", ruta)
    conn = db.get_connection(ruta)
    with conn:
        conn.execute("INSERT INTO catalogo_precios (producto, precio_compra_centavos, lote_minimo, tasa_iva_pct) VALUES (?, ?, ?, ?)",
            ("Insulina glargina", 12550, 5, 16))
    conn.close()
    resultado = calcular_presupuesto("2026-10-22", db_path=ruta)
    linea = next(p for p in resultado["financiadas"] if p["producto"] == "Insulina glargina")
    assert linea["precio_unitario_mxn"] == 125.50
    assert linea["lote_minimo"] == 5
    assert linea["cantidad_sugerida"] % 5 == 0
    assert linea["tasa_iva_pct"] == 16
    assert linea["total_centavos"] > 0
