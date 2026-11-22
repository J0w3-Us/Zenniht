import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { ReactElement, ReactNode } from 'react';
import type { ZenitState } from '../../lib/zenit-api';
import { ZenitPendingOrders } from './ZenitPendingOrders';
import { ZenitSuggestionsPage } from './ZenitSuggestionsPage';

function createState(): ZenitState {
  return {
    datos_cargados: true,
    filas: 4500,
    fecha_existencia: '2026-11-12',
    inferencia: null,
    productos: Array.from({ length: 50 }, (_, index) => ({
      producto: index === 0 ? 'Insulina glargina' : `Producto ${index + 1}`,
      cuadrante_kraljic: 'Estratégico',
      existencia: index === 0 ? 0 : 10,
      probabilidad: null,
      en_desabasto: null,
      orden: index === 0
        ? { id: 64, estado: 'pendiente' as const, cantidad_sugerida: null }
        : index === 1
          ? { id: 65, estado: 'aprobada' as const, cantidad_sugerida: null }
          : null,
    })),
  };
}

function findElement(
  node: ReactNode,
  matches: (element: ReactElement<Record<string, unknown> & { children?: ReactNode }>) => boolean,
): ReactElement<Record<string, unknown> & { children?: ReactNode }> | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findElement(child, matches);
      if (found) return found;
    }
    return null;
  }

  if (node === null || typeof node !== 'object' || !('type' in node)) return null;

  const element = node as ReactElement<Record<string, unknown> & { children?: ReactNode }>;
  if (matches(element)) return element;
  return findElement(element.props.children, matches);
}

describe('ZenitSuggestionsPage', () => {
  it('muestra estados de carga y vacío sin declarar válido un dataset ausente', () => {
    const loading = renderToStaticMarkup(
      <ZenitSuggestionsPage
        state={null}
        busy
        approvingOrderId={null}
        page={1}
        onPageChange={vi.fn()}
        onApprove={() => {}}
      />,
    );
    expect(loading).toContain('role="status"');
    expect(loading).toContain('aria-busy="true"');
    expect(loading).toContain('Consultando el estado local de las sugerencias');
    expect(loading).toContain('Conteo de sugerencias no disponible');
    expect(loading).toContain('<section');
    expect(loading).toContain('<h2 id="zenit-suggestions-title">Sugerencias</h2>');
    expect(loading).not.toContain('<main');
    expect(loading).not.toContain('<h1');
    expect(loading).not.toContain('Dataset validado');

    const empty = renderToStaticMarkup(
      <ZenitSuggestionsPage
        state={null}
        busy={false}
        approvingOrderId={null}
        page={1}
        onPageChange={vi.fn()}
        onApprove={() => {}}
      />,
    );
    expect(empty).toContain('Sin datos para revisar');
    expect(empty).toContain('Carga el dataset de ZENIT');
    expect(empty).not.toContain('Dataset validado');
  });

  it('cuenta sugerencias pendientes y aprueba solo la orden seleccionada', () => {
    const state = createState();
    const onApprove = vi.fn();
    const props = {
      state,
      busy: false,
      approvingOrderId: null,
      page: 1,
      onPageChange: vi.fn(),
      onApprove,
    };
    const page = ZenitSuggestionsPage(props);
    const ordersElement = findElement(
      page,
      (element) => element.type === ZenitPendingOrders,
    );

    expect(ordersElement).not.toBeNull();
    const html = renderToStaticMarkup(
      <ZenitSuggestionsPage {...props} />,
    );
    expect(html).not.toContain('Dataset validado: 4,500 filas y 50 productos.');
    expect(html).toContain('1 sugerencia pendiente');
    expect(html).toContain('Insulina glargina');
    expect(html).toContain('Cantidad por definir');
    expect(html).toContain('aprobación humana individual');
    expect(html).not.toContain('Aprobar todas');

    const orders = ZenitPendingOrders(
      ordersElement!.props as unknown as Parameters<typeof ZenitPendingOrders>[0],
    );
    const approveButton = findElement(
      orders,
      (element) => typeof element.type === 'function'
        && element.props['aria-label'] === 'Aprobar sugerencia para Insulina glargina',
    );

    expect(approveButton).not.toBeNull();
    (approveButton!.props as { onClick: () => void }).onClick();
    expect(onApprove).toHaveBeenCalledTimes(1);
    expect(onApprove).toHaveBeenCalledWith(64);
  });

  it('no muestra dataset validado si las filas o los productos no coinciden', () => {
    const state = createState();
    state.filas = 4499;
    const html = renderToStaticMarkup(
      <ZenitSuggestionsPage
        state={state}
        busy={false}
        approvingOrderId={null}
        page={1}
        onPageChange={vi.fn()}
        onApprove={() => {}}
      />,
    );

    expect(html).toContain('Dataset no validado.');
    expect(html).not.toContain('Dataset validado:');
    expect(html).not.toContain('Aprobar sugerencia para Insulina glargina');
  });

  it('muestra como máximo 20 sugerencias pendientes por página', () => {
    const state = createState();
    state.productos = Array.from({ length: 50 }, (_, index) => ({
      producto: `Producto ${index + 1}`,
      cuadrante_kraljic: 'Estratégico',
      existencia: 10,
      probabilidad: null,
      en_desabasto: null,
      orden: { id: index + 1, estado: 'pendiente' as const, cantidad_sugerida: null },
    }));

    const firstPage = renderToStaticMarkup(
      <ZenitSuggestionsPage
        state={state}
        busy={false}
        approvingOrderId={null}
        page={1}
        onPageChange={vi.fn()}
        onApprove={vi.fn()}
      />,
    );
    const lastPage = renderToStaticMarkup(
      <ZenitSuggestionsPage
        state={state}
        busy={false}
        approvingOrderId={null}
        page={3}
        onPageChange={vi.fn()}
        onApprove={vi.fn()}
      />,
    );

    expect((firstPage.match(/<li/g) ?? [])).toHaveLength(20);
    expect(firstPage).toContain('Mostrando 1 a 20 de 50');
    expect((lastPage.match(/<li/g) ?? [])).toHaveLength(10);
    expect(lastPage).toContain('Mostrando 41 a 50 de 50');
    expect(lastPage).toContain('Producto 50');
  });
});
