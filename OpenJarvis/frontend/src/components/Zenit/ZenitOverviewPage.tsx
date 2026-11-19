import {
  AlertTriangle,
  ArrowRight,
  Check,
  Database,
  LoaderCircle,
  Upload,
} from 'lucide-react';
import type { ZenitProduct, ZenitState } from '../../lib/zenit-api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { paginateItems, ZenitPagination, ZENIT_PAGE_SIZE } from './ZenitPagination';
import type { ZenitProductFilter } from './zenit-product-filters';
import './ZenitOverviewPage.css';

interface ZenitOverviewPageProps {
  state: ZenitState | null;
  loading: boolean;
  uploading: boolean;
  predicting: boolean;
  dateCutoff: string;
  onDateCutoffChange: (value: string) => void;
  onLoadDataset: () => void;
  onPredict: () => void;
  onOpenInventory: () => void;
  onOpenSuggestions: () => void;
  onFilterProducts: (filter: Exclude<ZenitProductFilter, 'search'>) => void;
  onProductSelect: (productName: string) => void;
  alertPage: number;
  onAlertPageChange: (page: number) => void;
}

function isValidDataset(state: ZenitState | null): boolean {
  return Boolean(
    state?.datos_cargados && state.filas === 4500 && state.productos.length === 50,
  );
}

function hasCompletePrediction(dataset: ZenitState | null): boolean {
  return Boolean(dataset?.inferencia)
    && Boolean(dataset?.productos.every(
      (product) => product.probabilidad !== null && product.en_desabasto !== null,
    ));
}

export function ZenitOverviewPage({
  state,
  loading,
  uploading,
  predicting,
  dateCutoff,
  onDateCutoffChange,
  onLoadDataset,
  onPredict,
  onOpenInventory,
  onOpenSuggestions,
  onFilterProducts,
  onProductSelect,
  alertPage,
  onAlertPageChange,
}: ZenitOverviewPageProps) {
  const dataset = isValidDataset(state) ? state : null;
  const stocks = dataset?.productos
    .map((product) => product.existencia)
    .filter((existencia): existencia is number => (
      typeof existencia === 'number' && Number.isInteger(existencia) && existencia >= 0
    )) ?? [];
  const hasStockSnapshot = Boolean(dataset?.fecha_existencia) && stocks.length === 50;
  const totalUnits = hasStockSnapshot
    ? stocks.reduce((total, existencia) => total + existencia, 0)
    : null;
  const outOfStockCount = hasStockSnapshot
    ? stocks.filter((existencia) => existencia === 0).length
    : null;
  const predictionIsValid = hasCompletePrediction(dataset);
  const alertProducts = predictionIsValid && dataset
    ? dataset.productos.filter(
      (product): product is ZenitProduct & {
        probabilidad: number;
        en_desabasto: true;
      } => product.en_desabasto === true && product.probabilidad !== null,
    )
    : [];
  const pendingCount = dataset?.productos.filter(
    (product) => product.orden?.estado === 'pendiente',
  ).length ?? null;
  const datasetStatus = loading && state === null
    ? 'Consultando'
    : dataset
      ? 'Validado'
      : state === null
        ? 'Pendiente'
        : 'No válido';
  const datasetStatusClass = dataset
    ? 'is-success'
    : state !== null && !loading
      ? 'is-error'
      : 'is-pending';
  const paginatedAlerts = paginateItems(alertProducts, alertPage);

  return (
    <section
      className="zenit-overview-page"
      aria-labelledby="zenit-overview-title"
      aria-busy={loading || uploading || predicting}
      aria-label="Resumen de inventario de ZENIT"
    >
      <header className="zenit-overview-header">
        <div>
          <p className="zenit-overview-eyebrow">La Esperanza · Inventario</p>
          <h2 id="zenit-overview-title">Resumen de inventario</h2>
          <p className="zenit-overview-description">
            Existencias registradas y alertas TFT, con sus fechas de referencia claramente separadas.
          </p>
        </div>
        <div className="zenit-overview-stock-date">
          <span>Último corte de existencias</span>
          <strong>{hasStockSnapshot ? dataset?.fecha_existencia : 'Sin datos'}</strong>
        </div>
      </header>

      <section className="zenit-overview-metrics" aria-label="Indicadores de inventario y desabasto">
        <button
          type="button"
          className="zenit-overview-metric"
          aria-label="Unidades disponibles. Abrir inventario completo."
          disabled={!hasStockSnapshot}
          onClick={() => onFilterProducts('all')}
        >
          <span className="zenit-overview-metric-label">Unidades disponibles</span>
          <strong>{totalUnits === null ? '—' : totalUnits.toLocaleString('es-MX')}</strong>
          <span className="zenit-overview-metric-detail">
            {hasStockSnapshot ? `En los 50 productos · ${dataset?.fecha_existencia}` : 'Carga el dataset para consultar existencias'}
          </span>
          <span className="zenit-overview-metric-action">
            Abrir inventario <ArrowRight aria-hidden="true" size={14} />
          </span>
        </button>

        <button
          type="button"
          className={`zenit-overview-metric${outOfStockCount ? ' is-warning' : ' is-clear'}`}
          aria-label="Productos sin existencia. Filtrar inventario."
          disabled={!hasStockSnapshot}
          onClick={() => onFilterProducts('out-of-stock')}
        >
          <span className="zenit-overview-metric-label">Productos sin existencia</span>
          <strong>{outOfStockCount === null ? '—' : outOfStockCount}</strong>
          <span className="zenit-overview-metric-detail">
            {hasStockSnapshot ? 'Existencia igual a cero en el último corte' : 'Sin corte de existencias disponible'}
          </span>
          <span className="zenit-overview-metric-action">
            Ver productos <ArrowRight aria-hidden="true" size={14} />
          </span>
        </button>

        <button
          type="button"
          className={`zenit-overview-metric${alertProducts.length ? ' is-alert' : ' is-clear'}`}
          aria-label="Alertas TFT a 7 días. Abrir alertas."
          disabled={!predictionIsValid}
          onClick={() => onFilterProducts('risk')}
        >
          <span className="zenit-overview-metric-label">Alertas TFT · 7 días</span>
          <strong>{predictionIsValid ? alertProducts.length : 'Sin predicción'}</strong>
          <span className="zenit-overview-metric-detail">
            {predictionIsValid && dataset?.inferencia
              ? `Corte de predicción · ${dataset.inferencia.fecha_corte}`
              : 'Requiere una inferencia TFT válida'}
          </span>
          <span className="zenit-overview-metric-action">
            Ver alertas <ArrowRight aria-hidden="true" size={14} />
          </span>
        </button>

        <button
          type="button"
          className="zenit-overview-metric"
          aria-label="Sugerencias pendientes. Abrir revisión."
          disabled={!dataset}
          onClick={onOpenSuggestions}
        >
          <span className="zenit-overview-metric-label">Sugerencias pendientes</span>
          <strong>{pendingCount === null ? '—' : pendingCount}</strong>
          <span className="zenit-overview-metric-detail">
            {pendingCount === null ? 'Carga el dataset para consultar' : 'Requieren aprobación manual'}
          </span>
          <span className="zenit-overview-metric-action">
            Revisar sugerencias <ArrowRight aria-hidden="true" size={14} />
          </span>
        </button>
      </section>

      <div className="zenit-overview-grid">
        <section className="zenit-overview-alerts" aria-labelledby="zenit-overview-alerts-title">
          <header className="zenit-overview-section-heading">
            <div>
              <p className="zenit-overview-eyebrow">Pronóstico TFT</p>
              <h2 id="zenit-overview-alerts-title">Productos a revisar</h2>
            </div>
            {predictionIsValid && (
              <span className={`zenit-overview-alert-count${alertProducts.length ? ' has-alerts' : ''}`}>
                {alertProducts.length} {alertProducts.length === 1 ? 'alerta' : 'alertas'}
              </span>
            )}
          </header>

          {!dataset ? (
            <p className="zenit-overview-empty">
              Carga y valida el conjunto cerrado de 4,500 filas para comenzar.
            </p>
          ) : !predictionIsValid ? (
            <p className="zenit-overview-empty">
              Ejecuta el TFT local para consultar alertas reales; no se muestran riesgos de respaldo.
            </p>
          ) : alertProducts.length === 0 ? (
            <p className="zenit-overview-empty">
              El TFT no marcó alertas para el corte {dataset.inferencia?.fecha_corte}.
              Esto no cambia el conteo de existencias del último día registrado.
            </p>
          ) : (
            <ul className="zenit-overview-alert-list">
              {paginatedAlerts.items.map((product) => (
                <li key={product.producto}>
                  <div className="zenit-overview-alert-product">
                    <strong>{product.producto}</strong>
                    <span>{product.cuadrante_kraljic}</span>
                  </div>
                  <span className="zenit-overview-alert-risk">
                    {(product.probabilidad * 100).toFixed(1)}%
                  </span>
                  <button
                    type="button"
                    onClick={() => onProductSelect(product.producto)}
                    aria-label={`Abrir ${product.producto} en el inventario`}
                  >
                    <ArrowRight aria-hidden="true" size={16} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {predictionIsValid && (
            <ZenitPagination
              label="alertas TFT"
              page={paginatedAlerts.page}
              totalItems={alertProducts.length}
              onPageChange={onAlertPageChange}
            />
          )}

          {predictionIsValid && alertProducts.length > ZENIT_PAGE_SIZE && (
            <button
              type="button"
              className="zenit-overview-all-alerts"
              onClick={() => onFilterProducts('risk')}
            >
              Abrir las {alertProducts.length} alertas en inventario
              <ArrowRight aria-hidden="true" size={15} />
            </button>
          )}
        </section>

        <section className="zenit-overview-analysis" aria-labelledby="zenit-overview-analysis-title">
          <header className="zenit-overview-section-heading">
            <div>
              <p className="zenit-overview-eyebrow">Análisis local</p>
              <h2 id="zenit-overview-analysis-title">Dataset y predicción</h2>
            </div>
            <span className={`zenit-overview-dataset-status ${datasetStatusClass}`}>
              {dataset ? <Check aria-hidden="true" size={15} /> : <Database aria-hidden="true" size={15} />}
              {datasetStatus}
            </span>
          </header>

          <p className="zenit-overview-analysis-copy">
            {dataset
              ? `Validado: ${state?.filas.toLocaleString('es-MX')} filas y 50 productos.`
              : state === null
                ? 'Carga el dataset canónico para habilitar el TFT.'
                : 'Se requieren 4,500 filas y exactamente 50 productos.'}
            {predictionIsValid && dataset?.inferencia
              ? ` Inferencia: ${dataset.inferencia.tiempo_inferencia_ms.toFixed(2)} ms, corte ${dataset.inferencia.fecha_corte}.`
              : ''}
          </p>

          <div className="zenit-overview-date-field">
            <label htmlFor="zenit-overview-date-cutoff">Fecha de corte TFT</label>
            <Input
              id="zenit-overview-date-cutoff"
              type="date"
              min="2026-09-11"
              max="2026-11-05"
              value={dateCutoff}
              onChange={(event) => onDateCutoffChange(event.target.value)}
              disabled={predicting}
              aria-describedby="zenit-overview-date-help"
            />
            <span id="zenit-overview-date-help">
              Del 11 de septiembre al 5 de noviembre de 2026.
            </span>
          </div>

          <div className="zenit-overview-actions">
            <Button
              type="button"
              variant="outline"
              className="zenit-overview-load-button"
              onClick={onLoadDataset}
              disabled={loading || uploading}
              aria-label={uploading ? 'Cargando dataset local' : 'Cargar dataset local'}
            >
              {uploading ? (
                <LoaderCircle aria-hidden="true" className="zenit-overview-spinner" />
              ) : (
                <Upload aria-hidden="true" />
              )}
              {uploading ? 'Cargando dataset…' : 'Cargar dataset local'}
            </Button>
            <Button
              type="button"
              onClick={onPredict}
              disabled={!dataset || loading || uploading || predicting}
              aria-label={predicting ? 'Calculando predicción TFT' : 'Predecir desabasto'}
            >
              {predicting ? (
                <LoaderCircle aria-hidden="true" className="zenit-overview-spinner" />
              ) : (
                <AlertTriangle aria-hidden="true" />
              )}
              {predicting ? 'Calculando…' : 'Predecir desabasto'}
            </Button>
          </div>

          <button
            type="button"
            className="zenit-overview-inventory-link"
            onClick={onOpenInventory}
            disabled={!dataset}
          >
            Abrir inventario completo
            <ArrowRight aria-hidden="true" size={15} />
          </button>
        </section>
      </div>
    </section>
  );
}
