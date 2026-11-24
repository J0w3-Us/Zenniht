"""Consultas operativas tipadas: intención explícita, sin SQL generado por IA."""
import re
from datetime import date, timedelta

import db
from politica_agente import normalizar


def planificar_consulta(texto, catalogo):
    """Resuelve peticiones claras de historial y ordenación antes del LLM."""
    limpio = normalizar(texto)
    dias_match = re.search(r"(?:ultimos?|ultimas?)\s+(\d+)\s+dias?", limpio)
    dias = min(90, max(1, int(dias_match[1]))) if dias_match else 14
    if re.search(r"\b(historial|historico|historica|evolucion)\b", limpio):
        argumentos = {"dias": 90 if re.search(r"\b(completo|completa|todo|todos)\b", limpio) and not dias_match else dias}
        candidatos = [p for p in catalogo if normalizar(p) in limpio]
        if not candidatos:
            candidatos = [p for p in catalogo if re.search(r"\b" + re.escape(normalizar(p).split()[0]) + r"\b", limpio)]
        if len(candidatos) == 1:
            argumentos["producto"] = candidatos[0]
        elif candidatos:
            argumentos["producto"] = normalizar(candidatos[0]).split()[0]
        else:
            especifico = re.search(r"historial(?:\s+de\s+ventas)?\s+de\s+(.+?)(?:\s+(?:en|durante|los|ultimos|desde)\b|$)", limpio)
            if especifico and not re.search(r"\b(inventario|farmacia|productos|ventas|todos|los|las)\b", especifico[1]):
                argumentos["producto"] = especifico[1].strip()
        fechas = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", limpio)
        if len(fechas) == 2:
            argumentos.update(fecha_inicio=fechas[0], fecha_fin=fechas[1])
        return [{"function": {"name": "consultar_historial_ventas", "arguments": argumentos}}]

    mayor = re.search(r"\b(mayor(?:es)?|mas|abundantes|top)\b", limpio)
    menor = re.search(r"\b(menor(?:es)?|menos)\b", limpio)
    ventas = re.search(r"\b(vendid\w*|ventas?)\b", limpio)
    cantidad = re.search(r"\b(cantidad|cantidades|existencias?|stock|unidades|tenemos|disponibles|inventario)\b", limpio)
    if (mayor or menor) and (cantidad or ventas):
        orden = ("ventas_asc" if menor else "ventas_desc") if ventas else ("existencia_asc" if menor else "existencia_desc")
        limite = re.search(r"\b(?:top|los|las|primeros|primeras)\s+(\d+)\b", limpio)
        argumentos = {"ordenar_por": orden, "limite": min(50, max(1, int(limite[1]))) if limite else 10}
        if ventas:
            argumentos["dias"] = dias if dias_match else 90
        return [{"function": {"name": "listar_productos_por_filtro", "arguments": argumentos}}]
    return None


def consultar_historial(db_path, producto="", dias=14, fecha_inicio=None, fecha_fin=None):
    dias = max(1, min(90, int(dias)))
    conn = db.get_connection(db_path)
    try:
        nombres = [f[0] for f in conn.execute("SELECT DISTINCT producto FROM ventas ORDER BY producto")]
        elegido = None
        if producto:
            coincidencias = [p for p in nombres if normalizar(producto) == normalizar(p)]
            coincidencias = coincidencias or [p for p in nombres if normalizar(producto) in normalizar(p)]
            if len(coincidencias) != 1:
                return {"coincidencias_multiples": coincidencias, "producto_no_encontrado": not coincidencias}
            elegido = coincidencias[0]
        ultimo = conn.execute("SELECT MAX(fecha) FROM ventas WHERE (? IS NULL OR producto = ?)", (elegido, elegido)).fetchone()[0]
        if not ultimo:
            return {"error": "Sin historial"}
        fin = date.fromisoformat(fecha_fin or ultimo)
        inicio = date.fromisoformat(fecha_inicio) if fecha_inicio else fin - timedelta(days=dias - 1)
        if inicio > fin or (fin - inicio).days >= 90:
            raise ValueError("La ventana de historial debe tener entre 1 y 90 días.")
        filas = conn.execute("""
            SELECT fecha, SUM(unidades_vendidas) AS unidades_vendidas, SUM(existencia) AS existencia
            FROM ventas WHERE fecha BETWEEN ? AND ? AND (? IS NULL OR producto = ?)
            GROUP BY fecha ORDER BY fecha
        """, (inicio.isoformat(), fin.isoformat(), elegido, elegido)).fetchall()
        registros = [dict(f) for f in filas]
        return {"producto": elegido, "agregado": elegido is None, "dias": len(registros), "historial": registros,
            "fecha_inicio": registros[0]["fecha"] if registros else None,
            "fecha_fin": registros[-1]["fecha"] if registros else None,
            "total_vendido": sum(f["unidades_vendidas"] for f in registros)}
    finally:
        conn.close()


def ventas_por_producto(db_path, dias=90):
    conn = db.get_connection(db_path)
    try:
        fin = conn.execute("SELECT MAX(fecha) FROM ventas").fetchone()[0]
        if not fin:
            return {}, None, None
        inicio = (date.fromisoformat(fin) - timedelta(days=max(1, min(90, int(dias))) - 1)).isoformat()
        filas = conn.execute("SELECT producto, SUM(unidades_vendidas) AS total FROM ventas WHERE fecha BETWEEN ? AND ? GROUP BY producto", (inicio, fin)).fetchall()
        return {f["producto"]: int(f["total"]) for f in filas}, inicio, fin
    finally:
        conn.close()
