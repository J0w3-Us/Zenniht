import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { ReactElement, ReactNode } from 'react';
import type { ZenitState } from '../../lib/zenit-api';
import canonicalCsv from '../../../../data/ventas.csv?raw';
import { ZenitOverviewPage } from './ZenitOverviewPage';

const COLUMNAS_CANONICAS = [
  'producto',
  'fecha',
  'unidades_vendidas',
  'existencia',
  'cuadrante_kraljic',
  'requiere_refrigeracion',
  'fecha_caducidad',
  'temperatura',
];

function createTftState(): ZenitState {
  return {
    datos_cargados: true,
    filas: 4500,
    fecha_existencia: '2026-11-12',
    inferencia: {
      fecha_corte: '2026-10-22',
      tiempo_inferencia_ms: 64.36,
      cumple_umbral_tiempo: true,
    },
    productos: Array.from({ length: 50 }, (_, index) => ({
      producto: `Producto ${index + 1}`,
      cuadrante_kraljic: 'Estratégico',
      existencia: index === 0 ? 0 : 10,
      probabilidad: index < 2 ? 0.72 : 0.18,
      en_desabasto: index === 0,
      orden: null,
    })),
  };
}

function renderPage(state: ZenitState | null) {
  return renderToStaticMarkup(
    <ZenitOverviewPage
      state={state}
      loading={false}
      uploading={false}
      predicting={false}
      dateCutoff="2026-10-22"
      onDateCutoffChange={vi.fn()}
      onLoadDataset={vi.fn()}
      onPredict={vi.fn()}
      onOpenInventory={vi.fn()}
      onOpenSuggestions={vi.fn()}
      onFilterProducts={vi.fn()}
      onProductSelect={vi.fn()}
      alertPage={1}
      onAlertPageChange={vi.fn()}
    />,
  );
}

function createCanonicalStockState(): ZenitState {
  const [header, ...lines] = canonicalCsv.trim().split(/\r?\n/);
  expect(header?.split(',')).toEqual(COLUMNAS_CANONICAS);

  const rows = lines.map((line) => {
    const values = line.split(',');
    expect(values).toHaveLength(COLUMNAS_CANONICAS.length);
    const [producto, fecha, , existencia, cuadrante_kraljic] = values;
    if (!producto || !fecha || existencia === undefined || !cuadrante_kraljic) {
      throw new Error('El CSV canónico contiene una fila incompleta.');
    }
    return {
      producto,
      fecha,
      existencia: Number(existencia),
      cuadrante_kraljic,
    };
  });
  expect(rows).toHaveLength(4500);

  const fecha_existencia = rows.reduce(
    (ultima, fila) => fila.fecha > ultima ? fila.fecha : ultima,
    rows[0]?.fecha ?? '',
  );
  const ultimoCorte = rows.filter((fila) => fila.fecha === fecha_existencia);
  expect(new Set(rows.map((fila) => fila.producto)).size).toBe(50);
  expect(ultimoCorte).toHaveLength(50);

  return {
    datos_cargados: true,
    filas: rows.length,
    fecha_existencia,
    inferencia: null,
    productos: ultimoCorte.map((fila) => ({
      producto: fila.producto,
      cuadrante_kraljic: fila.cuadrante_kraljic,
      existencia: fila.existencia,
      probabilidad: null,
      en_desabasto: null,
      orden: null,
    })),
  };
}

type TestElement = ReactElement<Record<string, unknown> & { children?: ReactNode }>;

function findElement(
  node: ReactNode,
  matches: (element: TestElement) => boolean,
): TestElement | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findElement(child, matches);
      if (found) return found;
    }
    return null;
  }
  if (node === null || typeof node !== 'object' || !('type' in node)) return null;

  const element = node as TestElement;
  if (matches(element)) return element;
  return findElement(element.props.children, matches);
}

describe('ZenitOverviewPage', () => {
  it('expone dataset y predicción pendientes cuando no hay estado', () => {
    const html = renderPage(null);

    expect(html).toContain('<section class="zenit-overview-page"');
    expect(html).toContain('<h2 id="zenit-overview-title">Resumen de inventario</h2>');
    expect(html).not.toContain('<main');
    expect(html).not.toContain('<h1');
    expect(html).toContain('Pendiente');
    expect(html).toContain('Carga y valida el conjunto cerrado');
    expect(html).toContain('Sin predicción');
    expect(html).toContain('Cargar dataset local');
    expect(html).toContain('Predecir desabasto');
    expect(html).toContain('min="2026-09-11"');
    expect(html).toContain('max="2026-11-05"');
    expect(html).toContain('disabled=""');
    expect(html).not.toContain('64.36 ms');
  });

  it('presenta solo las alertas reales del estado TFT y su tiempo de inferencia', () => {
    const html = renderPage(createTftState());

    expect(html).toContain('>Validado</span>');
    expect(html).toContain('2026-11-12');
    expect(html).toContain('>490</strong>');
    expect(html).toContain('Productos sin existencia');
    expect(html).toContain('>1</strong>');
    expect(html).toContain('Alertas TFT · 7 días');
    expect(html).toContain('64.36 ms');
    expect(html).toContain('2026-10-22');
    expect(html).toContain('1 alerta');
    expect(html).toContain('Abrir Producto 1 en el inventario');
    expect(html).not.toContain('>2 alertas');
  });

  it('calcula los KPI de existencia con los 4,500 registros del CSV canónico', () => {
    const state = createCanonicalStockState();
    const existencias = state.productos.map((producto) => producto.existencia ?? 0);
    const total = existencias.reduce((suma, existencia) => suma + existencia, 0);
    const sinExistencia = existencias.filter((existencia) => existencia === 0).length;
    const onFilterProducts = vi.fn();
    const onOpenSuggestions = vi.fn();
    const props = {
      state,
      loading: false,
      uploading: false,
      predicting: false,
      dateCutoff: '2026-10-22',
      onDateCutoffChange: vi.fn(),
      onLoadDataset: vi.fn(),
      onPredict: vi.fn(),
      onOpenInventory: vi.fn(),
      onOpenSuggestions,
      onFilterProducts,
      onProductSelect: vi.fn(),
      alertPage: 1,
      onAlertPageChange: vi.fn(),
    };
    const page = ZenitOverviewPage(props);
    const html = renderToStaticMarkup(page);

    expect(html).toContain(`>${total.toLocaleString('es-MX')}</strong>`);
    expect(html).toContain(`>${sinExistencia}</strong>`);
    expect(html).toContain(state.fecha_existencia ?? '');
    expect(html).toContain('Sin predicción');

    for (const label of [
      'Unidades disponibles. Abrir inventario completo.',
      'Productos sin existencia. Filtrar inventario.',
    ]) {
      const button = findElement(page, (element) => element.props['aria-label'] === label);
      const onClick = button?.props.onClick;
      if (typeof onClick === 'function') onClick();
    }
    const pendingButton = findElement(
      page,
      (element) => element.props['aria-label'] === 'Sugerencias pendientes. Abrir revisión.',
    );
    const onClick = pendingButton?.props.onClick;
    if (typeof onClick === 'function') onClick();

    expect(onFilterProducts.mock.calls).toEqual([['all'], ['out-of-stock']]);
    expect(onOpenSuggestions).toHaveBeenCalledOnce();
  });

  it('conecta cada KPI al filtro o pantalla correspondiente', () => {
    const onFilterProducts = vi.fn();
    const onOpenSuggestions = vi.fn();
    const props = {
      state: createTftState(),
      loading: false,
      uploading: false,
      predicting: false,
      dateCutoff: '2026-10-22',
      onDateCutoffChange: vi.fn(),
      onLoadDataset: vi.fn(),
      onPredict: vi.fn(),
      onOpenInventory: vi.fn(),
      onOpenSuggestions,
      onFilterProducts,
      onProductSelect: vi.fn(),
      alertPage: 1,
      onAlertPageChange: vi.fn(),
    };
    const page = ZenitOverviewPage(props);
    const kpiButtons = [
      findElement(page, (element) => element.props['aria-label'] === 'Unidades disponibles. Abrir inventario completo.'),
      findElement(page, (element) => element.props['aria-label'] === 'Productos sin existencia. Filtrar inventario.'),
      findElement(page, (element) => element.props['aria-label'] === 'Alertas TFT a 7 días. Abrir alertas.'),
      findElement(page, (element) => element.props['aria-label'] === 'Sugerencias pendientes. Abrir revisión.'),
    ];

    expect(kpiButtons.every(Boolean)).toBe(true);
    for (const button of kpiButtons) {
      const onClick = button?.props.onClick;
      if (typeof onClick === 'function') onClick();
    }

    expect(onFilterProducts.mock.calls).toEqual([['all'], ['out-of-stock'], ['risk']]);
    expect(onOpenSuggestions).toHaveBeenCalledOnce();
  });

  it('página las alertas TFT sin exceder 20 filas', () => {
    const state = createTftState();
    state.productos = state.productos.map((producto, index) => ({
      ...producto,
      probabilidad: 0.6 + index / 1000,
      en_desabasto: true,
    }));
    const props = {
      state,
      loading: false,
      uploading: false,
      predicting: false,
      dateCutoff: '2026-10-22',
      onDateCutoffChange: vi.fn(),
      onLoadDataset: vi.fn(),
      onPredict: vi.fn(),
      onOpenInventory: vi.fn(),
      onOpenSuggestions: vi.fn(),
      onFilterProducts: vi.fn(),
      onProductSelect: vi.fn(),
      alertPage: 3,
      onAlertPageChange: vi.fn(),
    };
    const html = renderToStaticMarkup(<ZenitOverviewPage {...props} />);

    expect((html.match(/<li/g) ?? [])).toHaveLength(10);
    expect(html).toContain('Mostrando 41 a 50 de 50');
    expect(html).toContain('Producto 50');
  });

  it('no habilita la predicción cuando las dimensiones del dataset no coinciden', () => {
    const state = createTftState();
    state.productos = state.productos.slice(0, 49);
    const html = renderPage(state);

    expect(html).toContain('No válido');
    expect(html).toContain('disabled=""');
    expect(html).not.toContain('Dataset listo para analizar');
  });
});
