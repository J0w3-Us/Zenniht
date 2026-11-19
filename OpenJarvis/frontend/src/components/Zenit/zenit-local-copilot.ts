import type { ZenitProduct, ZenitState } from '../../lib/zenit-api';
import { normalizeProductSearch } from './zenit-product-filters';

export type ZenitCopilotAction =
  | { type: 'load' }
  | { type: 'predict' }
  | { type: 'overview' }
  | { type: 'inventory'; filter: 'all' | 'strategic' | 'risk' | 'pending'; productName?: string }
  | { type: 'suggestions' };

export interface ZenitCopilotReply {
  text: string;
  action?: ZenitCopilotAction;
  actionLabel?: string;
}

function getStockSnapshot(
  state: ZenitState,
): { fecha: string; productos: Array<ZenitProduct & { existencia: number }> } | null {
  if (!state.fecha_existencia) return null;

  const productos = state.productos.filter(
    (product): product is ZenitProduct & { existencia: number } => (
      typeof product.existencia === 'number'
      && Number.isInteger(product.existencia)
      && product.existencia >= 0
    ),
  );
  return productos.length === 50
    ? { fecha: state.fecha_existencia, productos }
    : null;
}

function hasValidDataset(state: ZenitState | null): boolean {
  return Boolean(
    state?.datos_cargados && state.filas === 4500 && state.productos.length === 50,
  );
}

function hasCompletePrediction(state: ZenitState): boolean {
  return Boolean(state.inferencia)
    && state.productos.every(
      (product) => product.probabilidad !== null && product.en_desabasto !== null,
    );
}

function datasetRequired(): ZenitCopilotReply {
  return {
    text: 'Primero carga el dataset local validado: debe contener 4,500 filas y exactamente 50 productos.',
    action: { type: 'load' },
    actionLabel: 'Cargar dataset local',
  };
}

function resolveProductSearch(query: string, state: ZenitState | null): ZenitCopilotReply {
  if (!state) return datasetRequired();
  if (!hasValidDataset(state)) return datasetRequired();

  const searchTerm = normalizeProductSearch(
    query.replace(/^(?:buscar|busca|encuentra)\s*:?\s*/i, '').trim(),
  );
  if (!searchTerm) {
    return {
      text: 'Escribe el nombre de un producto después de “buscar”.',
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Abrir inventario',
    };
  }

  const products = state.productos;
  const exactMatch = products.find(
    (product) => normalizeProductSearch(product.producto) === searchTerm,
  );
  const matches = exactMatch
    ? [exactMatch]
    : products.filter((product) => normalizeProductSearch(product.producto).includes(searchTerm));

  if (matches.length === 0) {
    return {
      text: 'No encontré ese nombre entre los 50 productos del inventario local.',
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Ver inventario',
    };
  }

  if (matches.length > 1) {
    const names = matches.slice(0, 3).map((product) => product.producto).join(', ');
    return {
      text: `Encontré ${matches.length} coincidencias: ${names}. Escribe un nombre más específico.`,
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Ver inventario',
    };
  }

  const product = matches[0];
  if (!product) {
    return {
      text: 'No encontré ese nombre entre los 50 productos del inventario local.',
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Ver inventario',
    };
  }
  const predictionText = hasCompletePrediction(state)
    && product.probabilidad !== null
    && product.en_desabasto !== null
    ? `Riesgo TFT a 7 días: ${(product.probabilidad * 100).toFixed(1)}%. ${
      product.en_desabasto ? 'El modelo marcó alerta de desabasto.' : 'El modelo no marcó alerta.'
    }`
    : 'No hay una predicción TFT válida para consultar el riesgo.';
  const stockSnapshot = getStockSnapshot(state);
  const stockText = stockSnapshot && typeof product.existencia === 'number'
    ? `Existencia al ${stockSnapshot.fecha}: ${product.existencia.toLocaleString('es-MX')} unidades.`
    : '';

  return {
    text: `${product.producto} · ${product.cuadrante_kraljic}. ${stockText} ${predictionText}`.trim(),
    action: {
      type: 'inventory',
      filter: 'all',
      productName: product.producto,
    },
    actionLabel: 'Abrir producto en inventario',
  };
}

function resolveDatasetStatus(state: ZenitState | null): ZenitCopilotReply {
  if (!state) {
    return {
      text: 'Aún no hay un estado local disponible. Revisa la carga del dataset desde Resumen.',
      action: { type: 'overview' },
      actionLabel: 'Abrir Resumen',
    };
  }

  if (!hasValidDataset(state)) {
    return {
      text: `Dataset no validado: ${state.filas} filas y ${state.productos.length} productos. Se requieren 4,500 filas y exactamente 50 productos.`,
      action: { type: 'load' },
      actionLabel: 'Cargar dataset local',
    };
  }

  const prediction = hasCompletePrediction(state) && state.inferencia
    ? `Última inferencia TFT: ${state.inferencia.fecha_corte}, ${state.inferencia.tiempo_inferencia_ms.toFixed(2)} ms.`
    : 'Todavía no hay una inferencia TFT válida.';

  return {
    text: `Dataset validado: ${state.filas.toLocaleString('es-MX')} filas y ${state.productos.length} productos. ${prediction}`,
    action: hasCompletePrediction(state)
      ? { type: 'inventory', filter: 'all' }
      : { type: 'predict' },
    actionLabel: hasCompletePrediction(state) ? 'Abrir inventario' : 'Ejecutar TFT local',
  };
}

function resolvePredictionStatus(state: ZenitState | null): ZenitCopilotReply {
  if (!state) return datasetRequired();
  if (!hasValidDataset(state)) return datasetRequired();

  if (!hasCompletePrediction(state) || !state.inferencia) {
    return {
      text: 'No hay una inferencia TFT válida. Puedes ejecutar el modelo local; si falla, ZENIT mostrará el error y no sustituirá el resultado.',
      action: { type: 'predict' },
      actionLabel: 'Ejecutar TFT local',
    };
  }

  return {
    text: `La inferencia TFT está disponible para el ${state.inferencia.fecha_corte} y tardó ${state.inferencia.tiempo_inferencia_ms.toFixed(2)} ms.`,
    action: { type: 'inventory', filter: 'all' },
    actionLabel: 'Revisar los 50 productos',
  };
}

export function resolveZenitLocalQuery(
  query: string,
  state: ZenitState | null,
): ZenitCopilotReply {
  const normalized = normalizeProductSearch(query.trim());
  if (!normalized) {
    return { text: 'Escribe una pregunta sobre existencias, productos, alertas o sugerencias.' };
  }

  if (/^(?:buscar|busca|encuentra)(?:\s|:|$)/.test(normalized)) {
    return resolveProductSearch(query.trim(), state);
  }

  if (/\b(?:herramientas|recursos|ayuda|comandos)\b/.test(normalized)) {
    return {
      text: 'Puedo consultar las existencias registradas, las alertas de desabasto del TFT y las sugerencias pendientes, además de abrir productos del inventario. Las cantidades de reabasto siguen por definir y toda aprobación es manual.',
      action: { type: 'overview' },
      actionLabel: 'Abrir resumen',
    };
  }

  if (/\b(?:existencias?|stock|unidades|agotados?)\b/.test(normalized)) {
    if (!state) return datasetRequired();
    if (!hasValidDataset(state)) return datasetRequired();
    const snapshot = getStockSnapshot(state);
    if (!snapshot) {
      return {
        text: 'No hay un corte completo de existencias disponible; no puedo calcular el stock.',
        action: { type: 'overview' },
        actionLabel: 'Revisar dataset',
      };
    }

    const totalUnits = snapshot.productos.reduce(
      (total, product) => total + product.existencia,
      0,
    );
    const outOfStock = snapshot.productos.filter((product) => product.existencia === 0);
    const outOfStockText = outOfStock.length
      ? `Sin existencias: ${outOfStock.map((product) => product.producto).join(', ')}.`
      : 'No hay productos en cero existencias.';
    return {
      text: `Al último corte registrado (${snapshot.fecha}) hay ${totalUnits.toLocaleString('es-MX')} unidades en los 50 productos. ${outOfStockText}`,
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Abrir inventario',
    };
  }

  if (/\b(?:tft|modelo|prediccion|inferencia|pronostico)\b/.test(normalized)) {
    return resolvePredictionStatus(state);
  }

  if (/\b(?:pendientes?|sugerencias?|aprobar)\b/.test(normalized)) {
    if (!state) return datasetRequired();
    if (!hasValidDataset(state)) return datasetRequired();

    const pendingCount = state.productos.filter(
      (product) => product.orden?.estado === 'pendiente',
    ).length;
    return {
      text: pendingCount
        ? `Hay ${pendingCount} ${pendingCount === 1 ? 'sugerencia pendiente' : 'sugerencias pendientes'}. Cada aprobación es manual y la cantidad sigue por definir.`
        : 'No hay sugerencias pendientes en el inventario local.',
      action: { type: 'suggestions' },
      actionLabel: 'Revisar sugerencias',
    };
  }

  if (/\b(?:estrategicos?|kraljic)\b/.test(normalized)) {
    if (!state) return datasetRequired();
    if (!hasValidDataset(state)) return datasetRequired();
    const count = state.productos.filter(
      (product) => product.cuadrante_kraljic === 'Estratégico',
    ).length;
    return {
      text: `El dataset contiene ${count} ${count === 1 ? 'producto estratégico' : 'productos estratégicos'}.`,
      action: { type: 'inventory', filter: 'strategic' },
      actionLabel: 'Filtrar estratégicos',
    };
  }

  if (/\b(?:riesgo|riesgos)\b/.test(normalized)) {
    if (!state) return datasetRequired();
    if (!hasValidDataset(state)) return datasetRequired();
    if (!hasCompletePrediction(state)) {
      return {
        text: 'Aún no hay una inferencia TFT válida para ordenar los productos por riesgo.',
        action: { type: 'predict' },
        actionLabel: 'Ejecutar TFT local',
      };
    }

    const count = state.productos.filter(
      (product) => product.en_desabasto === true
        && product.probabilidad !== null
        && product.probabilidad >= 0.5,
    ).length;
    return {
      text: `${count} ${count === 1 ? 'producto supera' : 'productos superan'} el umbral de riesgo TFT del 50%.`,
      action: { type: 'inventory', filter: 'risk' },
      actionLabel: 'Ver riesgo ≥ 50%',
    };
  }

  if (/\b(?:desabasto|alertas?)\b/.test(normalized)) {
    if (!state) return datasetRequired();
    if (!hasValidDataset(state)) return datasetRequired();
    if (!hasCompletePrediction(state)) {
      return {
        text: 'Aún no hay alertas disponibles: falta una inferencia TFT válida.',
        action: { type: 'predict' },
        actionLabel: 'Ejecutar TFT local',
      };
    }

    const count = state.productos.filter((product) => product.en_desabasto === true).length;
    return {
      text: `El TFT marcó ${count} ${count === 1 ? 'producto con alerta' : 'productos con alerta'} de desabasto.`,
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Revisar inventario',
    };
  }

  if (/\b(?:inventario|productos|lista)\b/.test(normalized)) {
    if (!state) return datasetRequired();
    if (!hasValidDataset(state)) return datasetRequired();
    return {
      text: 'El inventario validado contiene exactamente 50 productos de La Esperanza.',
      action: { type: 'inventory', filter: 'all' },
      actionLabel: 'Abrir inventario',
    };
  }

  if (/\b(?:estado|dataset|datos)\b/.test(normalized)) {
    return resolveDatasetStatus(state);
  }

  return {
    text: 'Solo puedo consultar el inventario local, las alertas TFT, las sugerencias, los productos estratégicos y el estado del dataset. No genero respuestas fuera de estas consultas permitidas.',
  };
}
