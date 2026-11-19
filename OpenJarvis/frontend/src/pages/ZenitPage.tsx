import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { isTauri } from '@tauri-apps/api/core';
import {
  AlertTriangle,
  Database,
  LayoutDashboard,
  PackageSearch,
  ShoppingBasket,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { ZenitOverviewPage } from '../components/Zenit/ZenitOverviewPage';
import { ZenitProductSearch } from '../components/Zenit/ZenitProductSearch';
import { ZenitSuggestionsPage } from '../components/Zenit/ZenitSuggestionsPage';
import { ZenitLocalCopilot } from '../components/Zenit/ZenitLocalCopilot';
import { InventoryTable } from '../components/Zenit/InventoryTable';
import { paginateItems, ZenitPagination } from '../components/Zenit/ZenitPagination';
import {
  getVisibleZenitProducts,
  type ZenitProductFilter,
} from '../components/Zenit/zenit-product-filters';
import {
  approveZenitOrder,
  getZenitStartupError,
  getZenitState,
  loadZenitCanonicalDataset,
  predictZenitStock,
  uploadZenitDataset,
  type ZenitState,
} from '../lib/zenit-api';
import './ZenitPage.css';

const FECHA_DEMO = '2026-10-22';
type ZenitScreen = 'overview' | 'inventory' | 'suggestions';

const SCREEN_COPY: Record<ZenitScreen, { title: string; description: string }> = {
  overview: {
    title: 'Dashboard',
    description: 'Existencias registradas y alertas de desabasto a siete días.',
  },
  inventory: {
    title: 'Inventario',
    description: 'Revisa productos, alertas y prioridad de atención.',
  },
  suggestions: {
    title: 'Sugerencias',
    description: 'Revisa cada sugerencia antes de aprobarla.',
  },
};

function getErrorMessage(error: unknown): string {
  if (error instanceof TypeError) {
    return 'No se pudo conectar con la API local de ZENIT. Comprueba el arranque de la aplicación y las dependencias preparadas.';
  }
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado.';
}

function LoadingState() {
  return (
    <div className="zenit-loading" role="status" aria-busy="true">
      <div className="zenit-loading-line" />
      <span>Consultando el inventario local…</span>
    </div>
  );
}

export function ZenitPage() {
  const fileInput = useRef<HTMLInputElement>(null);
  const contentElement = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<ZenitState | null>(null);
  const [dateCutoff, setDateCutoff] = useState(FECHA_DEMO);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [approvingOrderId, setApprovingOrderId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [productFilter, setProductFilter] = useState<ZenitProductFilter>('all');
  const [sortByRisk, setSortByRisk] = useState(false);
  const [selectedProductName, setSelectedProductName] = useState<string | null>(null);
  const [activeScreen, setActiveScreen] = useState<ZenitScreen>('overview');
  const [inventoryPage, setInventoryPage] = useState(1);
  const [suggestionsPage, setSuggestionsPage] = useState(1);
  const [alertsPage, setAlertsPage] = useState(1);

  const refreshState = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const startupError = await getZenitStartupError();
      if (startupError) throw new Error(startupError);
      setState(await getZenitState());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshState();
  }, [refreshState]);

  useEffect(() => {
    contentElement.current?.scrollTo({ top: 0 });
  }, [activeScreen]);

  const handleUpload = async (file?: File) => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadZenitDataset(file);
      setState(await getZenitState());
      setProductFilter('all');
      setSortByRisk(false);
      setSelectedProductName(null);
      setInventoryPage(1);
      setSuggestionsPage(1);
      setAlertsPage(1);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  const handleLoadDataset = async () => {
    if (!isTauri()) {
      fileInput.current?.click();
      return;
    }

    setUploading(true);
    setError(null);
    try {
      await loadZenitCanonicalDataset();
      setState(await getZenitState());
      setProductFilter('all');
      setSortByRisk(false);
      setSelectedProductName(null);
      setInventoryPage(1);
      setSuggestionsPage(1);
      setAlertsPage(1);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setUploading(false);
    }
  };

  const handlePredict = async () => {
    setPredicting(true);
    setAlertsPage(1);
    setError(null);
    setState((current) => current && ({
      ...current,
      inferencia: null,
      productos: current.productos.map((product) => ({
        ...product,
        probabilidad: null,
        en_desabasto: null,
        orden: null,
      })),
    }));
    try {
      setState(await predictZenitStock(dateCutoff));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setPredicting(false);
    }
  };

  const handleApprove = async (orderId: number) => {
    setApprovingOrderId(orderId);
    setError(null);
    try {
      await approveZenitOrder(orderId);
      setState(await getZenitState());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setApprovingOrderId(null);
    }
  };

  const products = state?.productos ?? [];
  const hasValidProductSet = Boolean(
    state?.datos_cargados && state.filas === 4500 && products.length === 50,
  );
  const hasPrediction = Boolean(
    hasValidProductSet
      && state?.inferencia
      && products.every(
        (product) => product.probabilidad !== null && product.en_desabasto !== null,
      ),
  );
  const visibleProducts = useMemo(
    () => getVisibleZenitProducts(products, {
      filter: productFilter,
      sortByRisk,
      selectedProductName,
    }),
    [products, productFilter, selectedProductName, sortByRisk],
  );
  const paginatedProducts = paginateItems(visibleProducts, inventoryPage);
  const productViewLabel: Record<ZenitProductFilter, string> = {
    all: 'Todos los productos',
    strategic: 'Productos estratégicos',
    risk: 'Riesgo TFT ≥ 50%',
    'out-of-stock': 'Productos sin existencia',
    pending: 'Sugerencias pendientes',
    search: selectedProductName ?? 'Producto seleccionado',
  };
  const handleFilterChange = (filter: Exclude<ZenitProductFilter, 'search'>) => {
    setProductFilter(filter);
    setSelectedProductName(null);
    setSortByRisk(filter === 'risk');
    setInventoryPage(1);
    setActiveScreen('inventory');
  };
  const handleProductSelect = (productName: string | null) => {
    setSelectedProductName(productName);
    setInventoryPage(1);
    if (productName) {
      setProductFilter('search');
      setSortByRisk(false);
      setActiveScreen('inventory');
    } else {
      setProductFilter((current) => current === 'search' ? 'all' : current);
    }
  };
  return (
    <>
    <main className="zenit-page">
      <a className="zenit-skip-link" href="#zenit-main-content">
        Saltar al contenido principal
      </a>
      <div className="zenit-shell">
        <input
          ref={fileInput}
          id="zenit-csv"
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(event) => void handleUpload(event.currentTarget.files?.[0])}
          disabled={uploading || predicting}
        />
        <aside className="zenit-sidebar" aria-label="Navegación principal">
          <div className="zenit-brand" aria-label="ZENIT para La Esperanza">
            <span className="zenit-brand-mark"><Database aria-hidden="true" size={18} /></span>
            <span className="zenit-brand-copy">
              <strong>ZENIT</strong>
              <span>La Esperanza</span>
            </span>
          </div>
          <nav className="zenit-nav" aria-label="Pantallas">
            <p className="zenit-nav-label">Análisis</p>
            <button
              type="button"
              className="zenit-nav-link"
              aria-current={activeScreen === 'overview' ? 'page' : undefined}
              onClick={() => setActiveScreen('overview')}
            >
              <LayoutDashboard aria-hidden="true" size={17} />
              Resumen
            </button>
            <button
              type="button"
              className="zenit-nav-link"
              aria-current={activeScreen === 'inventory' ? 'page' : undefined}
              onClick={() => setActiveScreen('inventory')}
            >
              <PackageSearch aria-hidden="true" size={17} />
              Inventario
            </button>
            <button
              type="button"
              className="zenit-nav-link"
              aria-current={activeScreen === 'suggestions' ? 'page' : undefined}
              onClick={() => setActiveScreen('suggestions')}
            >
              <ShoppingBasket aria-hidden="true" size={17} />
              Sugerencias
            </button>
          </nav>
          <div className="zenit-sidebar-foot">
            <p>Predicción TFT local · CPU</p>
          </div>
        </aside>

        <div className="zenit-main">
          <header className="zenit-header">
            <div className="zenit-header-copy">
              <p className="zenit-eyebrow">LA ESPERANZA · OPERACIÓN LOCAL</p>
              <h1 className="zenit-title">{SCREEN_COPY[activeScreen].title}</h1>
              <p className="zenit-lead">{SCREEN_COPY[activeScreen].description}</p>
            </div>
            <div className="zenit-header-actions">
              {activeScreen === 'overview' && (
                <div className="zenit-header-date">
                  <span>Fecha de corte</span>
                  <strong>{dateCutoff}</strong>
                </div>
              )}
              <div className={`zenit-model-status${hasPrediction ? ' is-ready' : ''}`}>
                <span className="zenit-status-dot" />
                {hasPrediction ? 'Inferencia TFT disponible' : 'TFT · CPU local'}
              </div>
            </div>
          </header>

          <div
            ref={contentElement}
            className="zenit-content"
            id="zenit-main-content"
            tabIndex={-1}
          >
            {error && (
              <div className="zenit-error-banner" role="alert">
                <AlertTriangle aria-hidden="true" size={18} />
                <div>
                  <p className="zenit-message-title">No se pudo completar la operación</p>
                  <p>{error}</p>
                </div>
                {!state && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="zenit-secondary-action"
                    onClick={() => void refreshState()}
                  >
                    Reintentar
                  </Button>
                )}
              </div>
            )}

            {activeScreen === 'overview' && (
              <ZenitOverviewPage
                state={state}
                loading={loading}
                uploading={uploading}
                predicting={predicting}
                dateCutoff={dateCutoff}
                onDateCutoffChange={setDateCutoff}
                onLoadDataset={() => void handleLoadDataset()}
                onPredict={() => void handlePredict()}
                onOpenInventory={() => handleFilterChange('all')}
                onOpenSuggestions={() => {
                  setSuggestionsPage(1);
                  setActiveScreen('suggestions');
                }}
                onFilterProducts={handleFilterChange}
                onProductSelect={handleProductSelect}
                alertPage={alertsPage}
                onAlertPageChange={setAlertsPage}
              />
            )}

            {activeScreen === 'inventory' && (
              <section aria-labelledby="zenit-inventory-title">
                <div className="zenit-screen-header">
                  <div>
                    <p className="zenit-screen-kicker">La Esperanza · 50 productos</p>
                    <h2 className="zenit-screen-title" id="zenit-inventory-title">Inventario</h2>
                    <p className="zenit-screen-description">Busca, filtra y prioriza los productos con riesgo de desabasto.</p>
                  </div>
                  <div className="zenit-inventory-tools">
                    <div className="zenit-product-search">
                      <ZenitProductSearch
                        state={state}
                        hasValidDataset={hasValidProductSet}
                        onProductSelect={handleProductSelect}
                      />
                    </div>
                  </div>
                </div>

                {loading && !state ? (
                  <LoadingState />
                ) : !hasValidProductSet ? (
                  <section className="zenit-empty" aria-labelledby="zenit-inventory-empty-title">
                    <span className="zenit-empty-icon"><Database aria-hidden="true" size={20} /></span>
                    <div>
                      <h2 id="zenit-inventory-empty-title">Carga el dataset canónico</h2>
                      <p>El inventario aparece después de validar los 4,500 registros y los 50 productos.</p>
                    </div>
                    <Button type="button" className="zenit-primary-action" onClick={() => setActiveScreen('overview')}>
                      Ir al resumen
                    </Button>
                  </section>
                ) : (
                  <>
                    <div className="zenit-filter-bar" role="group" aria-label="Filtrar productos">
                      {([
                        ['all', 'Todos'],
                        ['strategic', 'Estratégicos'],
                        ['risk', 'Riesgo ≥ 50%'],
                        ['out-of-stock', 'Sin existencia'],
                        ['pending', 'Pendientes'],
                      ] as const).map(([filter, label]) => (
                        <button
                          key={filter}
                          type="button"
                          className="zenit-filter-button"
                          aria-pressed={productFilter === filter}
                          onClick={() => handleFilterChange(filter)}
                        >
                          {label}
                        </button>
                      ))}
                      {sortByRisk && (
                        <span className="zenit-filter-active">Riesgo descendente</span>
                      )}
                      {productFilter !== 'all' && (
                        <Button type="button" variant="outline" size="sm" onClick={() => handleFilterChange('all')}>
                          Restablecer
                        </Button>
                      )}
                      <span className="zenit-inventory-count" aria-live="polite">
                        {productViewLabel[productFilter]} · {visibleProducts.length} de 50
                      </span>
                    </div>
                    {!hasPrediction && (
                      <div className="zenit-prediction-note">
                        <AlertTriangle aria-hidden="true" size={17} />
                        <span>Sin predicción TFT. Ejecuta el análisis desde Resumen para ver riesgos.</span>
                      </div>
                    )}
                    <p className="zenit-table-hint">Desliza la tabla horizontalmente para consultar todas las columnas.</p>
                    <div className="zenit-table-frame">
                      <InventoryTable
                        products={paginatedProducts.items}
                        stockDate={state?.fecha_existencia ?? null}
                        approvingOrderId={approvingOrderId}
                        actionsDisabled={uploading || predicting || loading}
                        onApprove={(orderId) => void handleApprove(orderId)}
                      />
                    </div>
                    <ZenitPagination
                      label="productos"
                      page={paginatedProducts.page}
                      totalItems={visibleProducts.length}
                      onPageChange={setInventoryPage}
                    />
                  </>
                )}
              </section>
            )}

            {activeScreen === 'suggestions' && (
              <ZenitSuggestionsPage
                state={state}
                busy={loading || uploading || predicting}
                approvingOrderId={approvingOrderId}
                page={suggestionsPage}
                onPageChange={setSuggestionsPage}
                onApprove={(orderId) => void handleApprove(orderId)}
              />
            )}
          </div>
        </div>
      </div>
    </main>
    <ZenitLocalCopilot
      state={state}
      busy={loading || uploading || predicting || approvingOrderId !== null}
      onLoadDataset={handleLoadDataset}
      onPredict={handlePredict}
      onOpenScreen={setActiveScreen}
      onFilterChange={handleFilterChange}
      onProductSelect={handleProductSelect}
    />
    </>
  );
}
