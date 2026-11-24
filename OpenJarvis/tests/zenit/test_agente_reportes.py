"""Pruebas para verificar la resolución de los reportes de ZENIT:
- Reporte 1 y 2: Renderizado tabular dinámico de 3 columnas con alerta roja 🔴.
- Reporte 4: Desensibilización de consultas legítimas de desabasto/falla sin bloqueos indebidos.
- Reporte 5: Flag render_widget condicional para evitar componentes gráficos en errores.
"""
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

import politica_agente
from zenit_api import app

cliente = TestClient(app)


def test_desensibilizacion_consultas_desabasto_falla():
    texto1 = "¿Cuál es la falla crítica que tenemos con el desabasto?"
    texto2 = "Pásame una lista de datos con la información recopilada ya que necesitamos saber de los desabastos"
    
    assert politica_agente.dentro_del_alcance(texto1), "La consulta sobre 'falla crítica con desabasto' no debe ser rechazada."
    assert politica_agente.dentro_del_alcance(texto2), "La consulta sobre 'datos recopilados de desabastos' no debe ser rechazada."


def test_tabla_3_conceptos_con_alerta_roja():
    catalogo = {"Insulina glargina", "Vacuna influenza", "Paracetamol 500mg", "Ibuprofeno 400mg"}
    filas = [
        {"producto": "Insulina glargina", "existencia": 0, "probabilidad_tft": 0.99, "cantidad_sugerida": 90, "lote_minimo": 5},
        {"producto": "Vacuna influenza", "existencia": 4, "probabilidad_tft": 0.98, "cantidad_sugerida": 80, "lote_minimo": 5},
        {"producto": "Paracetamol 500mg", "existencia": 450, "probabilidad_tft": 0.05, "cantidad_sugerida": 0, "lote_minimo": 50},
        {"producto": "Ibuprofeno 400mg", "existencia": 320, "probabilidad_tft": 0.02, "cantidad_sugerida": 0, "lote_minimo": 40},
    ]

    tabla = politica_agente._tabla_3_conceptos(filas, catalogo)
    
    # 1. Verificar encabezado exacto de 3 columnas
    assert "| Medicamento | Stock Actual | Sugerencia de Reabastecimiento |" in tabla
    
    # 2. Verificar indicador de alerta roja 🔴 en productos críticos
    assert "🔴 **Insulina glargina**" in tabla
    assert "🔴 **Vacuna influenza**" in tabla
    
    # 3. Productos sin alerta no deben llevar el círculo rojo
    assert "| Paracetamol 500mg |" in tabla


def test_render_widget_en_chat_api():
    # Consulta de saludo/social: render_widget debe ser False
    resp_saludo = cliente.post("/api/zenit/agente/chat", json={"mensaje": "Hola buenas tardes"})
    assert resp_saludo.status_code == 200
    data_saludo = resp_saludo.json()
    assert data_saludo["render_widget"] is False

    # Consulta con mock de ejecución exitosa
    mock_chat = {
        "respuesta": "Al corte actual se detectaron 2 medicamentos en alerta crítica.",
        "modelo": "Zenit",
        "herramientas_usadas": [{"nombre": "ejecutar_prediccion_tft", "fuente": "TFT LOCAL"}],
        "fuentes": ["TFT LOCAL"],
        "estado_actualizado": None,
        "alertas": [{"producto": "Insulina glargina", "probabilidad": 0.99}],
        "mostrar_alertas": True,
        "ordenes_pendientes": [],
        "render_widget": True,
    }
    with patch("zenit_api.ejecutar_chat_agente", return_value=mock_chat):
        resp_alerta = cliente.post("/api/zenit/agente/chat", json={
            "mensaje": "Cuáles medicamentos tienen alerta de desabasto al corte actual",
            "fecha_corte": "2026-10-22"
        })
        assert resp_alerta.status_code == 200
        data_alerta = resp_alerta.json()
        assert data_alerta["render_widget"] is True
        assert len(data_alerta["alertas"]) > 0
