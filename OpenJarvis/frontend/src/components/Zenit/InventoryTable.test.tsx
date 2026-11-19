import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { InventoryTable } from './InventoryTable';
import type { ZenitProduct } from '../../lib/zenit-api';

function createProducts(): ZenitProduct[] {
  return Array.from({ length: 50 }, (_, index) => ({
    producto: `Producto ${index + 1}`,
    cuadrante_kraljic: 'Estratégico',
    existencia: index === 0 ? 0 : 12,
    probabilidad: index === 0 ? 0.5 : 0.1,
    en_desabasto: index === 0,
    orden: index === 0
      ? { id: 1, estado: 'pendiente', cantidad_sugerida: null }
      : null,
  }));
}

describe('InventoryTable', () => {
  it('muestra exactamente 50 productos y distingue alertas y sugerencias manuales', () => {
    const html = renderToStaticMarkup(
      <InventoryTable
        products={createProducts()}
        stockDate="2026-11-12"
        approvingOrderId={null}
        actionsDisabled={false}
        onApprove={vi.fn()}
      />,
    );

    expect((html.match(/<tr/g) ?? [])).toHaveLength(51);
    expect(html).toContain('Riesgo de desabasto');
    expect(html).toContain('Existencia');
    expect(html).toContain('al 2026-11-12');
    expect(html).toContain('>0</td>');
    expect(html).toContain('Sin alerta');
    expect(html).toContain('zenit-risk-indicator is-alert');
    expect(html).toContain('aria-label="Riesgo TFT a 7 días: 50.0%"');
    expect(html).toContain('Cantidad por definir');
    expect(html).toContain('title="Regla de reabasto pendiente de acuerdo"');
    expect(html).toMatch(/<button[^>]*class="zenit-order-quantity"[^>]*disabled=""/);
    expect(html).toContain('Aprobar sugerencia para Producto 1');
    expect(html).toContain('aria-valuenow="50"');
  });

  it('no inventa riesgo cuando todavía no existe una predicción', () => {
    const products = createProducts().map((product) => ({
      ...product,
      probabilidad: null,
      en_desabasto: null,
      orden: null,
    }));
    const html = renderToStaticMarkup(
      <InventoryTable
        products={products}
        stockDate="2026-11-12"
        approvingOrderId={null}
        actionsDisabled={false}
        onApprove={vi.fn()}
      />,
    );

    expect(html).toContain('Sin predicción');
    expect(html).not.toContain('Riesgo de desabasto');
    expect(html).not.toContain('role="meter"');
  });

  it('muestra la existencia vacía cuando la API local todavía no incluye ese campo', () => {
    const products = createProducts().map((product, index) => (
      index === 0 ? { ...product, existencia: undefined } : product
    ));
    const html = renderToStaticMarkup(
      <InventoryTable
        products={products}
        stockDate={null}
        approvingOrderId={null}
        actionsDisabled={false}
        onApprove={vi.fn()}
      />,
    );

    expect(html).toContain('<td class="zenit-stock-cell">—</td>');
  });

  it('deshabilita todas las aprobaciones mientras una está en curso', () => {
    const html = renderToStaticMarkup(
      <InventoryTable
        products={createProducts()}
        stockDate="2026-11-12"
        approvingOrderId={1}
        actionsDisabled={false}
        onApprove={vi.fn()}
      />,
    );

    const approvalButton = html.match(
      /<button[^>]*aria-label="Aprobar sugerencia para Producto 1"[^>]*>/,
    )?.[0];
    expect(approvalButton).toContain('disabled=""');
  });
});
