import { renderToStaticMarkup } from 'react-dom/server';
import type { ReactElement, ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { paginateItems, ZenitPagination, ZENIT_PAGE_SIZE } from './ZenitPagination';

type TestElement = ReactElement<Record<string, unknown> & { children?: ReactNode }>;

function findButton(node: ReactNode, label: string): TestElement | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findButton(child, label);
      if (found) return found;
    }
    return null;
  }
  if (node === null || typeof node !== 'object' || !('type' in node)) return null;

  const element = node as TestElement;
  if (element.props['aria-label'] === label) return element;
  return findButton(element.props.children, label);
}

describe('paginación ZENIT', () => {
  it('limita cada página a 20 elementos y conserva los restantes en la página siguiente', () => {
    const items = Array.from({ length: 50 }, (_, index) => index + 1);
    const firstPage = paginateItems(items, 1);
    const secondPage = paginateItems(items, 2);
    const thirdPage = paginateItems(items, 3);

    expect(ZENIT_PAGE_SIZE).toBe(20);
    expect(firstPage.items).toHaveLength(20);
    expect(firstPage.items[0]).toBe(1);
    expect(firstPage.items[firstPage.items.length - 1]).toBe(20);
    expect(secondPage.items[0]).toBe(21);
    expect(secondPage.items[secondPage.items.length - 1]).toBe(40);
    expect(thirdPage.items).toEqual([41, 42, 43, 44, 45, 46, 47, 48, 49, 50]);
  });

  it('ajusta páginas inválidas y estados que superan el número de páginas', () => {
    const items = Array.from({ length: 21 }, (_, index) => index);

    expect(paginateItems(items, 0).page).toBe(1);
    expect(paginateItems(items, Number.NaN).page).toBe(1);
    expect(paginateItems(items, 8).page).toBe(2);
  });

  it('expone navegación accesible e informa el rango actual', () => {
    const onPageChange = vi.fn();
    const html = renderToStaticMarkup(
      <ZenitPagination
        label="productos"
        page={2}
        totalItems={50}
        onPageChange={onPageChange}
      />,
    );

    expect(html).toContain('aria-label="Paginación de productos"');
    expect(html).toContain('Mostrando 21 a 40 de 50');
    expect(html).toContain('Página 2 de 3');
    expect(html).toContain('aria-label="Página anterior de productos"');
    expect(html).toContain('aria-label="Página siguiente de productos"');
  });

  it('no muestra controles cuando todos los elementos caben en una página', () => {
    const html = renderToStaticMarkup(
      <ZenitPagination label="sugerencias" page={1} totalItems={20} onPageChange={vi.fn()} />,
    );

    expect(html).toBe('');
  });

  it('cambia de página y deshabilita los límites de navegación', () => {
    const onPageChange = vi.fn();
    const pagination = ZenitPagination({
      label: 'productos',
      page: 1,
      totalItems: 50,
      onPageChange,
    });
    const nextButton = findButton(pagination, 'Página siguiente de productos');
    const previousButton = findButton(pagination, 'Página anterior de productos');

    expect(nextButton).not.toBeNull();
    expect(previousButton?.props.disabled).toBe(true);
    const onClick = nextButton?.props.onClick;
    if (typeof onClick === 'function') onClick();
    expect(onPageChange).toHaveBeenCalledWith(2);

    const lastPage = ZenitPagination({
      label: 'productos',
      page: 3,
      totalItems: 50,
      onPageChange,
    });
    expect(findButton(lastPage, 'Página siguiente de productos')?.props.disabled).toBe(true);
  });
});
