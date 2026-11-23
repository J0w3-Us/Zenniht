# Acción ZENIT: Monitoreo de Cadena de Frío (nueva)

Protege los productos que se conservan entre 2 y 8 °C.

---

## 1. Propósito
Registrar la temperatura de los equipos de refrigeración, detectar excursiones fuera de rango y evitar que un lote comprometido se venda sin que una persona lo revise.

## 2. Alcance
Los productos con `requiere_refrigeracion = 1`: Insulina glargina, Insulina NPH, Vacuna influenza y Vacuna hepatitis B. La columna `temperatura` de `ventas` es la temperatura ambiente y no sirve para esto.

## 3. Flujo
```
[ Lectura del refrigerador ] ─► [ ¿Entre 2 y 8 °C? ] ── sí ─► [ Se registra ]
                                       │ no
                                       ▼
        [ Excursión ] ─► [ Lotes del equipo en revisión ] ─► [ Decisión de una persona ]
```

## 4. Datos
Tabla `lecturas_frio`: equipo, fecha y hora (UTC), temperatura y quién la registró. En el prototipo no hay sensores: las lecturas se capturan a mano o se cargan de un CSV sintético aparte.

## 5. Reglas
- **Excursión:** una lectura menor a 2 °C o mayor a 8 °C. Se calcula la duración acumulada fuera de rango.
- **Lotes en revisión:** los lotes guardados en ese equipo pasan a `bloqueado` y dejan de sumar a la existencia vigente hasta que se decida.
- **Sin lectura:** si pasa más de dos veces el intervalo esperado (propuesta: lecturas cada 4 horas), aparece la alerta «sin datos».
- **Decisión:** la toma el responsable según las indicaciones del fabricante de cada producto (ZENIT no inventa tiempos de tolerancia). Opciones: liberar, mantener en cuarentena o registrar como merma. Todo queda en `bitacora`.

## 6. Relación con el abasto
Un lote bloqueado reduce la existencia vigente, lo que puede disparar una alerta de desabasto. Los productos Estratégicos refrigerados, como las insulinas, se revisan primero (Kraljic).

## 7. Cómo se verifica
Una lectura de 9.5 °C crea una excursión y bloquea los lotes del equipo; una lectura de 5 °C no; la falta de lecturas genera la alerta; liberar un lote exige usuario y motivo.
