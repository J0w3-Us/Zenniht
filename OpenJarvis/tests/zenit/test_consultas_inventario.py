"""La intención de historial y cantidades no se transforma en desabasto."""
import pytest
from fastapi.testclient import TestClient

import agente_zenit
import db
import zenit_api


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    ruta = tmp_path / "consultas.db"
    db.cargar_csv(db.CSV_PATH, ruta)
    monkeypatch.setattr(zenit_api, "DB_PATH", ruta)
    def no_llamar(*args, **kwargs):
        pytest.fail("Esta consulta debe resolverse con datos locales, sin LLM ni predicción")
    monkeypatch.setattr(agente_zenit, "obtener_estado_ollama", no_llamar)
    monkeypatch.setattr(agente_zenit.httpx, "post", no_llamar)
    monkeypatch.setattr(zenit_api, "_predecir_lote", no_llamar)
    return TestClient(zenit_api.app), ruta


@pytest.mark.parametrize("mensaje,orden,titulo", [
    ("Dame los 5 productos que tenemos en mayor cantidad", "DESC", "mayores existencias"),
    ("¿Cuáles son los 5 medicamentos con menos existencias?", "ASC", "menores existencias"),
])
def test_orden_de_existencias_con_datos_reales(cliente, mensaje, orden, titulo):
    api, ruta = cliente
    body = api.post("/api/zenit/agente/chat", json={"mensaje": mensaje}).json()
    conn = db.get_connection(ruta)
    filas = conn.execute(f"SELECT producto, existencia FROM ventas WHERE fecha = (SELECT MAX(fecha) FROM ventas) ORDER BY existencia {orden}, producto LIMIT 5").fetchall()
    conn.close()
    texto = body["respuesta"]
    assert titulo in texto
    assert "Mostrando 5 de 50" in texto
    assert [texto.index(f['producto']) for f in filas] == sorted(texto.index(f['producto']) for f in filas)
    for fila in filas:
        assert f"{fila['producto']}: {fila['existencia']:,} unidades" in texto
    assert "riesgo" not in texto and "alerta" not in texto
    assert body["mostrar_alertas"] is False
    assert body["sugerencias_destacadas_ids"] == []


def test_historial_de_producto_en_orden_cronologico(cliente):
    api, ruta = cliente
    body = api.post("/api/zenit/agente/chat", json={"mensaje": "Dame el historial de Insulina glargina de los últimos 7 días"}).json()
    conn = db.get_connection(ruta)
    filas = list(reversed(conn.execute("SELECT fecha, unidades_vendidas, existencia FROM ventas WHERE producto = ? ORDER BY fecha DESC LIMIT 7", ("Insulina glargina",)).fetchall()))
    conn.close()
    assert "Historial de Insulina glargina" in body["respuesta"]
    assert "(7 días)" in body["respuesta"]
    assert "| Fecha | Unidades Vendidas | Existencia en Stock |" in body["respuesta"]
    for fila in filas:
        assert f"| {fila['fecha']} | {fila['unidades_vendidas']:,} unidades | {fila['existencia']:,} unidades |" in body["respuesta"]
    assert body["herramientas_usadas"][0]["nombre"] == "consultar_historial_ventas"
    assert body["mostrar_alertas"] is False


def test_historial_general_suma_ventas_diarias_sin_inventar_producto(cliente):
    api, ruta = cliente
    texto = api.post("/api/zenit/agente/chat", json={"mensaje": "Dame el historial general de los últimos 7 días"}).json()["respuesta"]
    conn = db.get_connection(ruta)
    total = conn.execute("SELECT SUM(unidades_vendidas) FROM ventas WHERE fecha >= date((SELECT MAX(fecha) FROM ventas), '-6 days')").fetchone()[0]
    conn.close()
    assert "Historial general de la farmacia" in texto
    assert f"Total vendido: {total:,} unidades" in texto
    assert "| Fecha | Unidades Vendidas | Existencia en Stock |" in texto
    assert texto.count(" unidades |") == 14  # 7 filas x 2 columnas de unidades


def test_historial_completo_y_rango_explicito(cliente):
    api, _ = cliente
    completo = api.post("/api/zenit/agente/chat", json={"mensaje": "Dame todo el historial de Paracetamol"}).json()["respuesta"]
    assert "| Fecha | Unidades Vendidas | Existencia en Stock |" in completo
    assert completo.count(" unidades |") == 180  # 90 filas x 2
    rango = api.post("/api/zenit/agente/chat", json={"mensaje": "Historial de Losartan desde 2026-10-01 hasta 2026-10-03"}).json()["respuesta"]
    assert "Historial de Losartán 50 mg" in rango
    assert rango.count("vendidas;") == 3


def test_no_elige_un_producto_arbitrario_si_el_nombre_es_ambiguo(cliente):
    api, _ = cliente
    texto = api.post("/api/zenit/agente/chat", json={"mensaje": "Dame el historial de Insulina"}).json()["respuesta"]
    assert "¿De cuál" in texto and "Insulina glargina" in texto and "Insulina NPH" in texto
    assert "vendidas;" not in texto


def test_mas_vendidos_ordena_ventas_no_existencias(cliente):
    api, ruta = cliente
    body = api.post("/api/zenit/agente/chat", json={"mensaje": "Dame los 3 productos más vendidos en los últimos 7 días"}).json()
    conn = db.get_connection(ruta)
    filas = conn.execute("SELECT producto, SUM(unidades_vendidas) AS total FROM ventas WHERE fecha >= date((SELECT MAX(fecha) FROM ventas), '-6 days') GROUP BY producto ORDER BY total DESC, producto LIMIT 3").fetchall()
    conn.close()
    assert "Productos más vendidos" in body["respuesta"]
    for fila in filas:
        assert f"vendidas en el periodo: {fila['total']:,}" in body["respuesta"]
    assert body["mostrar_alertas"] is False


def test_restricciones_se_mantienen_aunque_se_mencione_historial(cliente):
    api, _ = cliente
    body = api.post("/api/zenit/agente/chat", json={"mensaje": "Dame código Python para consultar el historial"}).json()
    assert body["herramientas_usadas"] == []
    assert "Solo puedo ayudarte" in body["respuesta"]
