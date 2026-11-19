import { ClipboardCheck, PackageCheck } from 'lucide-react';
import type { ZenitState } from '../../lib/zenit-api';
import { ZenitPendingOrders } from './ZenitPendingOrders';
import './ZenitSuggestionsPage.css';

interface ZenitSuggestionsPageProps {
  state: ZenitState | null;
  busy: boolean;
  approvingOrderId: number | null;
  page: number;
  onPageChange: (page: number) => void;
  onApprove: (orderId: number) => void;
}

function isValidDataset(state: ZenitState | null): boolean {
  return Boolean(
    state?.datos_cargados && state.filas === 4500 && state.productos.length === 50,
  );
}

export function ZenitSuggestionsPage({
  state,
  busy,
  approvingOrderId,
  page,
  onPageChange,
  onApprove,
}: ZenitSuggestionsPageProps) {
  const productos = state?.productos ?? [];
  const hasValidDataset = isValidDataset(state);
  const pendingCount = state
    ? productos.filter((producto) => producto.orden?.estado === 'pendiente').length
    : null;

  return (
    <section className="zenit-suggestions-page" aria-labelledby="zenit-suggestions-title" aria-busy={busy}>
      <header className="zenit-suggestions-header">
        <div className="zenit-suggestions-heading">
          <p className="zenit-suggestions-eyebrow">La Esperanza · Revisión local</p>
          <h2 id="zenit-suggestions-title">Sugerencias</h2>
          <p className="zenit-suggestions-description">
            Revisa las órdenes sugeridas por el análisis de desabasto antes de tomar una decisión.
          </p>
        </div>
        <div
          className="zenit-suggestions-count"
          aria-label={pendingCount === null
            ? 'Conteo de sugerencias no disponible'
            : `${pendingCount} ${pendingCount === 1 ? 'sugerencia pendiente' : 'sugerencias pendientes'}`}
        >
          <ClipboardCheck aria-hidden="true" size={20} />
          <span className="zenit-suggestions-count-value">{pendingCount ?? '—'}</span>
          <span className="zenit-suggestions-count-label">
            {pendingCount === null ? 'sin datos' : pendingCount === 1 ? 'pendiente' : 'pendientes'}
          </span>
        </div>
      </header>

      <section className="zenit-suggestions-guidance" aria-label="Condiciones de aprobación">
        <PackageCheck aria-hidden="true" size={20} />
        <p>
          Cada sugerencia requiere aprobación humana individual. La cantidad permanece por definir
          hasta que se acuerde una regla de reabasto.
        </p>
      </section>

      {state === null ? (
        busy ? (
          <div className="zenit-suggestions-state" role="status" aria-busy="true">
            <span className="zenit-suggestions-loading-mark" aria-hidden="true" />
            <p>Consultando el estado local de las sugerencias…</p>
          </div>
        ) : (
          <div className="zenit-suggestions-state" role="status">
            <h2>Sin datos para revisar</h2>
            <p>Carga el dataset de ZENIT para consultar sugerencias de desabasto.</p>
          </div>
        )
      ) : (
        <>
          <div
            className={`zenit-suggestions-dataset${hasValidDataset ? ' is-valid' : ' is-invalid'}`}
            role="status"
          >
            <span className="zenit-suggestions-dataset-indicator" aria-hidden="true" />
            {hasValidDataset
              ? 'Dataset validado: 4,500 filas y 50 productos.'
              : 'Dataset no validado. Se requieren 4,500 filas y exactamente 50 productos.'}
          </div>

          {hasValidDataset ? (
            <ZenitPendingOrders
              state={state}
              hasValidDataset={hasValidDataset}
              busy={busy}
              approvingOrderId={approvingOrderId}
              page={page}
              onPageChange={onPageChange}
              onApprove={onApprove}
            />
          ) : (
            <div className="zenit-suggestions-state" role="status">
              <h2>Sugerencias no disponibles</h2>
              <p>Verifica la carga del dataset antes de revisar o aprobar órdenes.</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
