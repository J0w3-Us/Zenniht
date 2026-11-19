import { describe, expect, it } from 'vitest';
import type { ZenitProduct } from '../../lib/zenit-api';
import { getVisibleZenitProducts, normalizeProductSearch } from './zenit-product-filters';

const products: ZenitProduct[] = [
  {
    producto: 'Insulina glargina',
    cuadrante_kraljic: 'Estratégico',
    existencia: 0,
    probabilidad: 0.5,
    en_desabasto: true,
    orden: { id: 1, estado: 'pendiente', cantidad_sugerida: null },
  },
  {
    producto: 'Paracetamol 500 mg',
    cuadrante_kraljic: 'Apalancamiento',
    existencia: 8,
    probabilidad: 0.82,
    en_desabasto: true,
    orden: null,
  },
  {
    producto: 'Gasas',
    cuadrante_kraljic: 'No crítico',
    existencia: 20,
    probabilidad: 0.1,
    en_desabasto: false,
    orden: { id: 2, estado: 'aprobada', cantidad_sugerida: null },
  },
];

describe('getVisibleZenitProducts', () => {
  it('filtra alertas desde el umbral acordado de 50%', () => {
    expect(getVisibleZenitProducts(products, {
      filter: 'risk',
      sortByRisk: false,
      selectedProductName: null,
    }).map((product) => product.producto)).toEqual([
      'Insulina glargina',
      'Paracetamol 500 mg',
    ]);
  });

  it('ordena por riesgo sin mutar el orden Kraljic recibido', () => {
    const ordered = getVisibleZenitProducts(products, {
      filter: 'all',
      sortByRisk: true,
      selectedProductName: null,
    });

    expect(ordered.map((product) => product.producto)).toEqual([
      'Paracetamol 500 mg',
      'Insulina glargina',
      'Gasas',
    ]);
    expect(products[0].producto).toBe('Insulina glargina');
  });

  it('limita la vista de pendientes a órdenes aún no aprobadas', () => {
    expect(getVisibleZenitProducts(products, {
      filter: 'pending',
      sortByRisk: false,
      selectedProductName: null,
    }).map((product) => product.producto)).toEqual(['Insulina glargina']);
  });

  it('filtra solo productos con existencia observada igual a cero', () => {
    expect(getVisibleZenitProducts(products, {
      filter: 'out-of-stock',
      sortByRisk: false,
      selectedProductName: null,
    }).map((product) => product.producto)).toEqual(['Insulina glargina']);
  });

  it('busca un producto seleccionado por coincidencia exacta', () => {
    expect(getVisibleZenitProducts(products, {
      filter: 'search',
      sortByRisk: false,
      selectedProductName: 'Gasas',
    }).map((product) => product.producto)).toEqual(['Gasas']);
  });
});

it('normaliza mayúsculas y acentos en la búsqueda local', () => {
  expect(normalizeProductSearch('INSÚLINA')).toBe('insulina');
});
