"""Frontera de producto: el chat publica datos operativos, nunca prosa del LLM.

El clasificador de entrada facilita el rechazo temprano. La garantía de salida
proviene del renderizado controlado y de las herramientas permitidas, no de
suponer que un prompt o una lista de palabras basta contra cualquier evasión.
"""
import math
import re
import unicodedata
from datetime import date

RECHAZO = "Solo puedo ayudarte con inventario, ventas, riesgo de desabasto, sugerencias de reabasto y cotizaciones de la farmacia."
ERROR_OPERACION = "No pude completar esa consulta con los datos de la farmacia. Revisa la información disponible e inténtalo de nuevo."
AYUDA = "Puedo consultar existencias e historial de ventas, revisar riesgo de desabasto a siete días y preparar cotizaciones de reabasto. ¿Qué necesitas revisar?"

HERRAMIENTAS_PERMITIDAS = frozenset({
    "consultar_resumen_inventario", "consultar_producto", "consultar_historial_ventas",
    "listar_productos_por_filtro", "ejecutar_prediccion_tft",
    "consultar_sugerencias_pendientes", "consultar_presupuesto_reabasto",
})


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).casefold()
    return "".join(c for c in texto if not unicodedata.combining(c) and unicodedata.category(c) != "Cf")


_PROHIBIDO = re.compile(
    r"```|\b(python|javascript|typescript|java|html|css|sql|powershell|bash|shell|script|pseudocodigo|programacion|programar|algoritmo|software|stack\s*trace|traceback|base64|rot13|jailbreak|developer|system\s*prompt|prompt|credenciales|contrasena|api\s*key)\b"
    r"|\bcodigo\b(?!\s+(?:de\s+)?(?:producto|barras|medicamento|articulo)\b)"
    r"|\b(code|coding|function|console\.log|print\s*\(|def\s+\w+|import\s+\w+)"
    r"|\b(ignora|ignore|olvida|omite|revela|muestra|cambia|desactiva|bypass)\b.{0,60}\b(instrucciones|reglas|restricciones|sistema|rol|prompt|instructions|rules)\b"
    r"|\b(receta\s+medica|diagnostico|diagnosticar|dosis|dosificacion|tratamiento|paciente|sintomas|tomar\s+para|automedicacion)\b",
    re.I | re.S,
)
_DOMINIO = re.compile(
    r"\b(inventario|historial|historico|historica|evolucion|existencias?|stock|ventas?|vendid\w*|"
    r"medicamentos?|insumos?|productos?|farmacia|desabasto|agot\w*|acabar\w*|terminar\w*|reabast\w*|"
    r"resurt\w*|sugerencias?|cotiz\w*|presupuest\w*|precios?|costos?|proveedores?|pedidos?|ordenes?|"
    r"kraljic|priorida\w*|clasific\w*|cuadrant\w*|distribu\w*|resumen|estrate\w*|cuello|apalanc\w*|rutinar\w*|"
    r"riesgos?|alertas?|predic\w*|pronostic\w*|caduc\w*|refriger\w*|cobertura|iva|lotes?|"
    r"comprar|compras?|falla\w*|critica\w*|recopilad\w*|datos|lista)\b"
)
_CORTO = re.compile(r"^(?:y\s+)?(?:si|no|continua|sigue|todos|todas|muestralos|muestralas|detallalo|explicalo|mas\s+detalle|por\s+que|cuanto\s+cuesta|y\s+ese)[?¿!¡.,\s]*$")


def entrada_prohibida(texto):
    return len(texto) > 2000 or bool(_PROHIBIDO.search(normalizar(texto)))


def dentro_del_alcance(texto, historial=(), catalogo=()):
    if entrada_prohibida(texto):
        return False
    limpio = normalizar(texto)
    ranking_existencias = bool(
        re.search(r"\b(mayor(?:es)?|menor(?:es)?|mas|menos)\b", limpio)
        and re.search(r"\b(cantidad|cantidades|unidades|disponibles|stock)\b", limpio)
    )
    # Tolerancia a palabras unidas o errores tipográficos comunes en consultas de inventario
    tolerancia_inventario = bool(
        re.search(r"\b(unidades?\s*dispon\w*|distrib\w*|cuadrant\w*|priorid\w*|kraljic)\b", limpio)
    )
    if _DOMINIO.search(limpio) or ranking_existencias or tolerancia_inventario or any(normalizar(p) in limpio for p in catalogo if p):
        return True
    if _CORTO.fullmatch(limpio):
        return any(t.get("role") == "user" and not entrada_prohibida(t.get("content", ""))
                   and _DOMINIO.search(normalizar(t.get("content", ""))) for t in historial[-10:])
    return False


def respuesta_social(texto):
    limpio = normalizar(texto).strip(" ¿?¡!.,")
    if limpio in {"hola", "buenos dias", "buenas tardes", "buenas noches", "gracias", "muchas gracias", "ayuda", "que puedes hacer"}:
        return AYUDA
    if limpio in {"quien eres", "como te llamas", "cual es tu nombre"}:
        return "Soy Zenit, el asistente de inventario y reabasto de la farmacia."
    return None


def _numero(valor, decimales=0):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return "Sin dato"
    return f"{valor:,.{decimales}f}"


def _fecha(valor):
    try:
        return date.fromisoformat(str(valor)).isoformat()
    except ValueError:
        return "Sin fecha"


def _nombre(valor, catalogo):
    if valor not in catalogo:
        raise ValueError("Producto fuera del catálogo verificado.")
    # El catálogo es un dato, no Markdown ni instrucciones ejecutables.
    return re.sub(r"[\r\n`<>|\\\[\]{}*_]", " ", str(valor))[:160]


def _productos(filas, catalogo, mostrar_riesgo=True):
    lineas = []
    for p in filas[:50]:
        texto = f"- {_nombre(p['producto'], catalogo)}"
        if "existencia" in p:
            texto += f": {_numero(p['existencia'])} unidades"
        if "unidades_vendidas" in p:
            texto += f"; vendidas en el periodo: {_numero(p['unidades_vendidas'])}"
        riesgo = p.get("probabilidad_tft", p.get("probabilidad"))
        porcentaje = p.get("probabilidad_tft_porcentaje")
        if riesgo is not None:
            porcentaje = float(riesgo) * 100
        if porcentaje is not None and mostrar_riesgo:
            texto += f"; riesgo a siete días: {_numero(porcentaje, 1)}%"
        lineas.append(texto + ".")
    return "\n".join(lineas) if lineas else "No hay productos que mostrar con este criterio."


def _tabla_3_conceptos(filas, catalogo):
    """Genera tabla dinámica Markdown con exactamente 3 columnas y alerta roja."""
    if not filas:
        return "No hay productos que mostrar con este criterio."
    
    # Si son menos de 3 productos, mostrar en formato conciso
    if len(filas) < 3:
        lineas = []
        for p in filas:
            nom = _nombre(p["producto"], catalogo)
            stock = _numero(p.get("existencia", 0))
            riesgo = float(p.get("probabilidad_tft", p.get("probabilidad", 0.0)) or 0.0)
            en_riesgo = riesgo >= 0.50 or int(p.get("existencia", 1)) == 0
            alerta = "🔴 " if en_riesgo else ""
            sug = p.get("cantidad_sugerida")
            sug_str = f"{_numero(sug)} unidades" if sug else "Por definir (requiere aprobación)"
            lineas.append(f"- {alerta}**{nom}**: {stock} unidades en stock; sugerencia de reabastecimiento: {sug_str}.")
        return "\n".join(lineas)

    encabezado = "| Medicamento | Stock Actual | Sugerencia de Reabastecimiento |\n| :--- | :---: | :---: |\n"
    cuerpo = []
    for p in filas[:50]:
        nom = _nombre(p["producto"], catalogo)
        stock = _numero(p.get("existencia", 0))
        riesgo = float(p.get("probabilidad_tft", p.get("probabilidad", 0.0)) or 0.0)
        en_riesgo = riesgo >= 0.50 or int(p.get("existencia", 1)) == 0
        
        sug = p.get("cantidad_sugerida")
        lote = p.get("lote_minimo", 1)
        if sug:
            num_lotes = max(1, int(sug) // max(1, int(lote)))
            sug_str = f"**{_numero(sug)} unidades** *({num_lotes} lotes de {lote})*"
        elif en_riesgo:
            sug_str = "**Reabasto prioritario** *(evaluando lote)*"
        else:
            sug_str = "No requerida *(cobertura suficiente)*"

        if en_riesgo:
            cuerpo.append(f"| 🔴 **{nom}** | **{stock} unidades** | {sug_str} |")
        else:
            cuerpo.append(f"| {nom} | {stock} unidades | {sug_str} |")

    return encabezado + "\n".join(cuerpo)



def renderizar_resultado(nombre, resultado, catalogo, incluir_alertas=False):
    """Solo campos conocidos y valores del dominio; nunca mensajes libres del LLM."""
    if nombre not in HERRAMIENTAS_PERMITIDAS or not isinstance(resultado, dict):
        return ERROR_OPERACION
    if resultado.get("error"):
        return ERROR_OPERACION
    try:
        if nombre == "consultar_resumen_inventario":
            if not resultado.get("datos_cargados"):
                return "Carga el historial de inventario antes de realizar la consulta."
            texto = (f"El inventario tiene {_numero(resultado['total_productos'])} productos y {_numero(resultado['filas'])} registros. "
                f"Al {_fecha(resultado['fecha_existencia'])} hay {_numero(resultado['unidades_totales'])} unidades disponibles.\n")
            
            dist_k = resultado.get("distribucion_kraljic")
            if dist_k and isinstance(dist_k, dict):
                partes_k = [f"{k}: {_numero(v)}" for k, v in dist_k.items()]
                texto += f"Distribución por cuadrantes Kraljic: {', '.join(partes_k)}.\n\n"
            else:
                texto += "\n"

            if incluir_alertas and not resultado.get("inferencia_tft"):
                texto += "Aún no hay una predicción calculada. Puedes solicitar el análisis de desabasto."
            elif incluir_alertas:
                texto += "Productos con alerta de desabasto:\n\n" + _tabla_3_conceptos(resultado.get("productos_en_alerta_tft", []), catalogo)
            else:
                texto += "Productos con mayores existencias:\n\n" + _tabla_3_conceptos(resultado.get("productos_mayor_existencia", []), catalogo)
                texto += f"\n\nSugerencias pendientes: {_numero(resultado.get('ordenes_pendientes', 0))}."
            sin_stock = resultado.get("productos_sin_existencia", [])
            if sin_stock:
                texto += "\n\nSin existencias al último corte:\n" + "\n".join(f"- 🔴 **{_nombre(p, catalogo)}**." for p in sin_stock[:50])
            return texto
        if nombre == "consultar_producto":
            if resultado.get("coincidencias_multiples"):
                return "Especifica uno de estos productos:\n" + "\n".join(f"- {_nombre(p, catalogo)}." for p in resultado["coincidencias_multiples"])
            if not resultado.get("producto"):
                return _productos(resultado.get("productos_menor_existencia", []), catalogo)
            texto = (f"{_nombre(resultado['producto'], catalogo)}: {_numero(resultado['existencia_actual'])} unidades "
                f"al {_fecha(resultado['fecha_ultimo_corte'])}.\n"
                f"Venta diaria promedio: {_numero(resultado['ventas_promedio_7d'], 2)} unidades en los últimos siete días "
                f"y {_numero(resultado['ventas_promedio_30d'], 2)} en los últimos treinta.\n"
                f"Caducidad registrada: {_fecha(resultado.get('fecha_caducidad'))}.")
            if resultado.get("probabilidad_tft") is not None:
                texto += f"\nRiesgo de desabasto a siete días: {_numero(float(resultado['probabilidad_tft']) * 100, 1)}%."
            return texto
        if nombre == "consultar_historial_ventas":
            if resultado.get("producto_no_encontrado"):
                return "No encontré ese producto en el catálogo. Indica el nombre con el que aparece en el inventario."
            if resultado.get("coincidencias_multiples"):
                return "¿De cuál de estos productos necesitas el historial?\n" + "\n".join(f"- {_nombre(p, catalogo)}." for p in resultado["coincidencias_multiples"])
            hist = resultado.get("historial", [])
            if not hist:
                return "No hay registros de ventas o existencias para ese periodo."
            titulo = "Historial general de la farmacia" if resultado.get("agregado") else f"Historial de {_nombre(resultado['producto'], catalogo)}"
            encabezado_info = (f"{titulo}, del {_fecha(resultado.get('fecha_inicio'))} al {_fecha(resultado.get('fecha_fin'))} "
                f"({_numero(resultado.get('dias'))} días). Total vendido: {_numero(resultado.get('total_vendido'))} unidades.\n\n")
            
            # Si el historial tiene 5 o más registros, estructurarlo en tabla Markdown
            if len(hist) >= 5:
                tabla_hist = ["| Fecha | Unidades Vendidas | Existencia en Stock |\n| :--- | :---: | :---: |"]
                for f in hist[:90]:
                    tabla_hist.append(f"| {_fecha(f['fecha'])} | {_numero(f['unidades_vendidas'])} unidades | {_numero(f['existencia'])} unidades |")
                return encabezado_info + "\n".join(tabla_hist)
            else:
                lineas_hist = [
                    f"- {_fecha(f['fecha'])}: {_numero(f['unidades_vendidas'])} vendidas; {_numero(f['existencia'])} en existencia."
                    for f in hist[:90]
                ]
                return encabezado_info + "\n".join(lineas_hist)
        if nombre == "listar_productos_por_filtro":
            orden = resultado.get("ordenar_por", "producto")
            titulos = {"producto": "Productos del inventario", "existencia_desc": "Productos con mayores existencias",
                "existencia_asc": "Productos con menores existencias", "ventas_desc": "Productos más vendidos", "ventas_asc": "Productos menos vendidos"}
            titulo = titulos.get(orden, "Productos del inventario")
            periodo = (f"Del {_fecha(resultado['fecha_inicio'])} al {_fecha(resultado['fecha_fin'])}. "
                if resultado.get("fecha_inicio") else f"Existencias al {_fecha(resultado.get('fecha_fin'))}. ")
            return (f"{titulo}. {periodo}Mostrando {_numero(len(resultado.get('productos', [])))} de {_numero(resultado['total_coincidencias'])}.\n"
                + _productos(resultado.get("productos", []), catalogo, mostrar_riesgo=resultado.get("solo_en_riesgo", False)))
        if nombre == "ejecutar_prediccion_tft":
            return (f"Predicción a siete días calculada para {_numero(resultado['total_productos_evaluados'])} productos "
                f"con corte al {_fecha(resultado['fecha_corte'])}.\n"
                f"Alertas de desabasto detectadas: {_numero(resultado['total_alertas'])}.\n\n" + _tabla_3_conceptos(resultado.get("alertas", []), catalogo))
        if nombre == "consultar_sugerencias_pendientes":
            pendientes = resultado.get("pendientes", [])
            if not pendientes:
                return "No hay sugerencias de reabasto pendientes en este momento."
            texto = f"Se encontraron {_numero(len(pendientes))} sugerencias de reabasto pendientes de aprobación:\n\n"
            filas_sug = []
            for p in pendientes[:50]:
                cant = p.get("cantidad_sugerida")
                cant_str = f"{_numero(cant)} unidades" if cant else "Por calcular con lote mínimo"
                filas_sug.append({
                    "producto": p["producto"],
                    "existencia": p.get("existencia", 0),
                    "probabilidad_tft": p.get("probabilidad_desabasto", 0.9),
                    "cantidad_sugerida": cant,
                    "lote_minimo": 5,
                })
            texto += _tabla_3_conceptos(filas_sug, catalogo)
            return texto + "\n\nRecuerda que estas órdenes requieren autorización manual antes de su emisión."
        if nombre == "consultar_presupuesto_reabasto":
            resumen = resultado["resumen"]
            filas = resultado.get("financiadas", [])
            texto = (f"Cotización estimada al {_fecha(resumen['fecha_corte'])}: subtotal ${_numero(resumen['subtotal_mxn'], 2)}, "
                f"IVA ${_numero(resumen['iva_mxn'], 2)} y total ${_numero(resumen['total_mxn'], 2)} MXN.\n")
            for p in filas[:50]:
                precio = p.get("precio_unitario_mxn")
                if not isinstance(precio, (int, float)) or precio <= 0:
                    texto += f"\n- {_nombre(p['producto'], catalogo)}: falta un precio válido; no puede cotizarse."
                else:
                    texto += (f"\n- {_nombre(p['producto'], catalogo)}: {_numero(p['cantidad_sugerida'])} unidades; "
                        f"precio unitario ${_numero(precio, 2)}; IVA {_numero(p['tasa_iva_pct'], 1)}%; "
                        f"total ${_numero(p['total_mxn'], 2)} MXN.")
            if resultado.get("no_financiadas"):
                texto += f"\nProductos fuera del presupuesto: {_numero(len(resultado['no_financiadas']))}."
            return texto + "\nEs una estimación; cualquier pedido requiere aprobación manual."
    except (KeyError, TypeError, ValueError, OverflowError):
        return ERROR_OPERACION
    return ERROR_OPERACION
