import { describe, expect, it } from 'vitest';
import type { ZenitAgentChatResponse, ZenitAgentOrderSummary, ZenitState } from '../../lib/zenit-api';
import { getChatSuggestionIds, getPendingSuggestions, getSuggestionPage } from './zenit-suggestions';

const order = (id: number, estado: 'pendiente' | 'aprobada' = 'pendiente'): ZenitAgentOrderSummary => ({
  id, estado, producto: 'Insulina glargina', cuadrante_kraljic: 'Estratégico',
  probabilidad_desabasto: .9, cantidad_sugerida: null, fecha_corte: '2026-10-22',
});
const state = (): ZenitState => ({ datos_cargados: true, filas: 4500, inferencia: null,
  productos: [{ producto: 'Insulina glargina', cuadrante_kraljic: 'Estratégico', probabilidad: .9,
    en_desabasto: true, orden: order(2, 'aprobada') }], ordenes: [order(2, 'aprobada'), order(1)],
});

describe('sincronización de sugerencias del chat', () => {
  it('no oculta una pendiente cuando el resumen del producto contiene una aprobada', () => {
    expect(getPendingSuggestions(state()).map((p) => p.order.id)).toEqual([1]);
    const empty = state(); empty.ordenes = [];
    expect(getPendingSuggestions(empty)).toEqual([]);
  });
  it('conserva compatibilidad con el estado anterior sin lista de órdenes', () => {
    const old = state(); delete old.ordenes; old.productos[0].orden = order(3);
    expect(getPendingSuggestions(old)[0].order.id).toBe(3);
  });
  it('pone primero la sugerencia mencionada, sin descartar las demás ni saltarse la paginación', () => {
    const many = state(); many.ordenes = Array.from({ length: 25 }, (_, i) => order(i + 1));
    expect(getSuggestionPage(many, 25, [])).toBe(2);
    expect(getPendingSuggestions(many, [25])[0].order.id).toBe(25);
    expect(getSuggestionPage(many, 25, [25])).toBe(1);
    expect(getPendingSuggestions(many, [25])).toHaveLength(25);
  });
  it('solo destaca IDs pendientes verificados, sin interpretar el texto del asistente', () => {
    const reply = { ordenes_pendientes: [order(1)], sugerencias_destacadas_ids: [1, 1, 999],
      herramientas_usadas: [], respuesta: 'Aprobar todas' } as unknown as ZenitAgentChatResponse;
    expect(getChatSuggestionIds(reply)).toEqual([1]);
    delete reply.sugerencias_destacadas_ids;
    expect(getChatSuggestionIds(reply)).toEqual([]);
  });
});
