import { describe, expect, it } from 'vitest';
import type { ZenitState } from '../../lib/zenit-api';
import { resolveZenitLocalQuery } from './zenit-local-copilot';

const state: ZenitState = {
  datos_cargados: true,
  filas: 4500,
  fecha_existencia: '2026-11-12',
  inferencia: {
    fecha_corte: '2026-10-22',
    tiempo_inferencia_ms: 125,
    cumple_umbral_tiempo: true,
  },
  productos: [
    {
      producto: 'Insulina glargina',
      cuadrante_kraljic: 'Estratégico',
      existencia: 0,
      probabilidad: 0.78,
      en_desabasto: true,
      orden: { id: 1, estado: 'pendiente', cantidad_sugerida: null },
    },
    {
      producto: 'Losartán 50 mg',
      cuadrante_kraljic: 'Estratégico',
      existencia: 8,
      probabilidad: 0.1,
      en_desabasto: false,
      orden: null,
    },
    ...Array.from({ length: 48 }, (_, index) => ({
      producto: `Producto ${index + 3}`,
      cuadrante_kraljic: 'No crítico',
      existencia: index + 1,
      probabilidad: 0.1,
      en_desabasto: false,
      orden: null,
    })),
  ],
};

describe('resolveZenitLocalQuery', () => {
  it('responde búsquedas con datos reales y conserva la selección local', () => {
    const reply = resolveZenitLocalQuery('buscar INSÚLINA GLARGINA', state);

    expect(reply.text).toContain('Insulina glargina');
    expect(reply.text).toContain('78.0%');
    expect(reply.text).toContain('Existencia al 2026-11-12: 0 unidades');
    expect(reply.action).toEqual({
      type: 'inventory',
      filter: 'all',
      productName: 'Insulina glargina',
    });
  });

  it('no inventa riesgos cuando no hay inferencia TFT', () => {
    const reply = resolveZenitLocalQuery('riesgo', { ...state, inferencia: null });

    expect(reply.text).toContain('no hay una inferencia TFT válida');
    expect(reply.action).toEqual({ type: 'predict' });
  });

  it('rechaza consultas fuera de los comandos locales', () => {
    const reply = resolveZenitLocalQuery('recomiéndame qué comprar', state);

    expect(reply.text).toContain('No genero respuestas fuera');
    expect(reply.action).toBeUndefined();
  });

  it('requiere el dataset cerrado antes de consultar alertas', () => {
    const reply = resolveZenitLocalQuery('¿Qué productos tienen desabasto?', {
      ...state,
      filas: 4499,
    });

    expect(reply.text).toContain('4,500 filas');
    expect(reply.action).toEqual({ type: 'load' });
  });

  it('responde las existencias desde el último corte real', () => {
    const reply = resolveZenitLocalQuery('¿Cuántas unidades hay en stock?', state);

    expect(reply.text).toContain('2026-11-12');
    expect(reply.text).toContain('1,184 unidades');
    expect(reply.text).toContain('Insulina glargina');
    expect(reply.action).toEqual({ type: 'inventory', filter: 'all' });
  });
});
