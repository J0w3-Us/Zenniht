"""Pruebas del agente local ZENIT (Ollama + herramientas SQLite/TFT + guardrails)."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import agente_zenit
import db
import zenit_api


@pytest.fixture
def cliente_con_datos(tmp_path, monkeypatch):
    db_path = tmp_path / "zenith.db"
    monkeypatch.setattr(zenit_api, "DB_PATH", db_path)
    db.cargar_csv(db.CSV_PATH, db_path)
    return TestClient(zenit_api.app), db_path


@pytest.mark.parametrize(
    "sql_prohibido",
    [
        "DROP TABLE ventas",
        "DELETE FROM ventas",
        "UPDATE ventas SET existencia = 0",
        "INSERT INTO ordenes VALUES (1)",
        "SELECT * FROM ventas; DROP TABLE ventas",
        "PRAGMA table_info(ventas)",
        "SELECT * FROM ventas -- comentario",
    ],
)
def test_guardrail_bloquea_sql_destructivo(sql_prohibido):
    with pytest.raises(ValueError):
        agente_zenit.validar_sql_solo_lectura(sql_prohibido)


def test_sql_solo_lectura_consulta_sqlite(cliente_con_datos):
    _, db_path = cliente_con_datos
    resultado = agente_zenit.ejecutar_sql_solo_lectura(
        "SELECT COUNT(*) AS total FROM ventas",
        db_path,
    )
    assert resultado["filas_devueltas"] == 1
    assert resultado["resultados"][0]["total"] == 4500


def test_herramientas_locales_consultan_producto_e_historial(cliente_con_datos):
    _, db_path = cliente_con_datos
    prod_info, cambio, fuente = agente_zenit.ejecutar_herramienta_local(
        "consultar_producto",
        {"nombre": "Insulina glargina"},
        db_path=db_path,
        obtener_estado_fn=zenit_api._obtener_estado,
        ejecutar_prediccion_fn=zenit_api._predecir_lote,
    )
    assert not cambio
    assert fuente == "SQLITE LOCAL"
    assert prod_info["producto"] == "Insulina glargina"
    assert prod_info["cuadrante_kraljic"] == "Estratégico"
    assert prod_info["requiere_refrigeracion"] is True

    hist, _, _ = agente_zenit.ejecutar_herramienta_local(
        "consultar_historial_ventas",
        {"producto": "Insulina glargina", "dias": 7},
        db_path=db_path,
        obtener_estado_fn=zenit_api._obtener_estado,
        ejecutar_prediccion_fn=zenit_api._predecir_lote,
    )
    assert hist["dias"] == 7
    assert len(hist["historial"]) == 7


def test_chat_agente_orquesta_tool_calling_ollama_y_tft(cliente_con_datos, monkeypatch):
    cliente, _ = cliente_con_datos
    llamadas_ollama = []

    def fake_get(url, timeout=1.5):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"models": [{"name": "qwen2.5:3b"}]},
        )

    def fake_post(url, json, timeout=120):
        llamadas_ollama.append(json)
        if len(llamadas_ollama) == 1:
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "consultar_resumen_inventario",
                                    "arguments": {},
                                }
                            }
                        ],
                    }
                },
            )
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "message": {
                    "role": "assistant",
                    "content": "El inventario tiene 50 productos y 4,500 registros validados en SQLite.",
                }
            },
        )

    monkeypatch.setattr(agente_zenit.httpx, "get", fake_get)
    monkeypatch.setattr(agente_zenit.httpx, "post", fake_post)

    resp = cliente.post(
        "/api/zenit/agente/chat",
        json={"mensaje": "¿Cuál es el estado del inventario?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["modelo"] == "qwen2.5:3b"
    assert "50 productos" in body["respuesta"]
    assert body["fuentes"] == ["SQLITE LOCAL"]
    assert body["herramientas_usadas"][0]["nombre"] == "consultar_resumen_inventario"


def test_chat_agente_informa_error_503_si_ollama_no_esta_activo(cliente_con_datos, monkeypatch):
    cliente, _ = cliente_con_datos

    def fake_get_error(url, timeout=1.5):
        raise agente_zenit.httpx.ConnectError("Connection refused")

    monkeypatch.setattr(agente_zenit.httpx, "get", fake_get_error)

    estado = cliente.get("/api/zenit/agente/estado")
    assert estado.status_code == 200
    assert estado.json()["ollama_disponible"] is False

    chat = cliente.post("/api/zenit/agente/chat", json={"mensaje": "Hola"})
    assert chat.status_code == 503
    assert "Ollama" in chat.json()["detail"]


def test_resumen_y_consultar_producto_vacio_devuelven_datos_utiles(cliente_con_datos):
    _, db_path = cliente_con_datos
    resumen, _, _ = agente_zenit.ejecutar_herramienta_local(
        "consultar_resumen_inventario",
        {},
        db_path=db_path,
        obtener_estado_fn=zenit_api._obtener_estado,
        ejecutar_prediccion_fn=zenit_api._predecir_lote,
    )
    assert "productos_en_alerta_tft" in resumen
    assert "productos_menor_existencia" in resumen
    assert len(resumen["productos_menor_existencia"]) == 5

    sin_nombre, _, _ = agente_zenit.ejecutar_herramienta_local(
        "consultar_producto",
        {"nombre": ""},
        db_path=db_path,
        obtener_estado_fn=zenit_api._obtener_estado,
        ejecutar_prediccion_fn=zenit_api._predecir_lote,
    )
    assert "error" not in sin_nombre
    assert len(sin_nombre["productos_menor_existencia"]) == 8
