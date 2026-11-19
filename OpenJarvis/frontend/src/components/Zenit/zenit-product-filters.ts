import type { ZenitProduct } from '../../lib/zenit-api';

export type ZenitProductFilter =
  | 'all'
  | 'strategic'
  | 'risk'
  | 'out-of-stock'
  | 'pending'
  | 'search';

interface ZenitProductView {
  filter: ZenitProductFilter;
  sortByRisk: boolean;
  selectedProductName: string | null;
}

export function normalizeProductSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('es-MX');
}

export function getVisibleZenitProducts(
  products: ZenitProduct[],
  view: ZenitProductView,
): ZenitProduct[] {
  const visible = products.filter((product) => {
    if (view.filter === 'strategic') return product.cuadrante_kraljic === 'Estratégico';
    if (view.filter === 'risk') {
      return product.en_desabasto === true
        && product.probabilidad !== null
        && product.probabilidad >= 0.5;
    }
    if (view.filter === 'out-of-stock') return product.existencia === 0;
    if (view.filter === 'pending') return product.orden?.estado === 'pendiente';
    if (view.filter === 'search') return product.producto === view.selectedProductName;
    return true;
  });

  if (!view.sortByRisk) return visible;

  return [...visible].sort(
    (left, right) => (right.probabilidad ?? -1) - (left.probabilidad ?? -1),
  );
}
