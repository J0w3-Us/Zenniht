import type { ZenitAgentChatResponse, ZenitOrder, ZenitProduct, ZenitState } from '../../lib/zenit-api';
import { ZENIT_PAGE_SIZE } from './ZenitPagination';

export interface PendingSuggestion {
  product: ZenitProduct;
  order: ZenitOrder;
}

export function getPendingSuggestions(state: ZenitState | null, highlightedIds: readonly number[] = []): PendingSuggestion[] {
  if (!state) return [];
  const products = new Map(state.productos.map((p) => [p.producto, p]));
  const pending = state.ordenes !== undefined
    ? state.ordenes.flatMap((order) => {
      const product = products.get(order.producto);
      return product && order.estado === 'pendiente' ? [{ product, order }] : [];
    })
    : state.productos.flatMap((product) => product.orden?.estado === 'pendiente'
      ? [{ product, order: product.orden }] : []);
  const highlighted = new Set(highlightedIds);
  return pending.sort((a, b) => Number(highlighted.has(b.order.id)) - Number(highlighted.has(a.order.id)));
}

export function getChatSuggestionIds(reply: ZenitAgentChatResponse): number[] {
  const pending = new Set(reply.ordenes_pendientes.map((o) => o.id));
  if (reply.sugerencias_destacadas_ids !== undefined) {
    return [...new Set(reply.sugerencias_destacadas_ids)].filter((id) => pending.has(id));
  }
  // Compatibilidad con el servidor anterior, sin deducir acciones del texto del modelo.
  const mentionsOrders = reply.herramientas_usadas.some((t) => [
    'consultar_sugerencias_pendientes', 'ejecutar_prediccion_tft',
  ].includes(t.nombre));
  return mentionsOrders ? [...pending] : [];
}

export function getSuggestionPage(state: ZenitState | null, orderId: number, highlightedIds: readonly number[]): number {
  const index = getPendingSuggestions(state, highlightedIds).findIndex((p) => p.order.id === orderId);
  return index < 0 ? 1 : Math.floor(index / ZENIT_PAGE_SIZE) + 1;
}
