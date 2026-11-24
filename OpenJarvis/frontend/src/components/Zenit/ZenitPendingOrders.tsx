import { Check, ClipboardList } from 'lucide-react';
import { Button } from '../ui/button';
import type { ZenitProduct, ZenitState } from '../../lib/zenit-api';
import { paginateItems, ZenitPagination } from './ZenitPagination';
import { getPendingSuggestions } from './zenit-suggestions';

interface ZenitPendingOrdersProps {
  state: ZenitState | null;
  hasValidDataset: boolean;
  busy: boolean;
  approvingOrderId: number | null;
  page: number;
  onPageChange: (page: number) => void;
  onApprove: (orderId: number) => void;
  highlightedOrderIds?: readonly number[];
}

export function ZenitPendingOrders({
  state,
  hasValidDataset,
  busy,
  approvingOrderId,
  page,
  onPageChange,
  onApprove,
  highlightedOrderIds = [],
}: ZenitPendingOrdersProps) {
  const pendingOrders = hasValidDataset ? getPendingSuggestions(state, highlightedOrderIds) : [];
  const paginatedOrders = paginateItems(pendingOrders, page);

  return (
    <section className="zenit-assistant-orders" aria-labelledby="zenit-assistant-orders-title">
      <div className="zenit-assistant-orders-heading">
        <h3 id="zenit-assistant-orders-title">
          <ClipboardList aria-hidden="true" size={15} />
          Aprobación manual
        </h3>
        <span>{pendingOrders.length}</span>
      </div>
      {pendingOrders.length ? (
        <ul>
          {paginatedOrders.items.map(({ product, order }) => (
            <li key={order.id} id={`zenit-suggestion-${order.id}`}
              className={highlightedOrderIds.includes(order.id) ? 'is-highlighted' : undefined}>
              <div>
                <strong>{product.producto}</strong>
                <span>Cantidad por definir</span>
                {highlightedOrderIds.includes(order.id) && <span className="zenit-suggestion-mentioned">Mencionada en el chat</span>}
              </div>
              <Button
                type="button"
                variant="outline"
                className="zenit-assistant-approve"
                disabled={busy || approvingOrderId !== null}
                aria-label={`Aprobar sugerencia para ${product.producto}`}
                onClick={() => onApprove(order.id)}
              >
                {approvingOrderId === order.id
                  ? 'Aprobando…'
                  : <><Check aria-hidden="true" size={14} /> Aprobar</>}
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p>No hay sugerencias para aprobar.</p>
      )}
      <ZenitPagination
        label="sugerencias"
        page={paginatedOrders.page}
        totalItems={pendingOrders.length}
        onPageChange={onPageChange}
      />
    </section>
  );
}
