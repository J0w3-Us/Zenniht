import { Check, ClipboardList } from 'lucide-react';
import { Button } from '../ui/button';
import type { ZenitProduct, ZenitState } from '../../lib/zenit-api';
import { paginateItems, ZenitPagination } from './ZenitPagination';

interface ZenitPendingOrdersProps {
  state: ZenitState | null;
  hasValidDataset: boolean;
  busy: boolean;
  approvingOrderId: number | null;
  page: number;
  onPageChange: (page: number) => void;
  onApprove: (orderId: number) => void;
}

export function ZenitPendingOrders({
  state,
  hasValidDataset,
  busy,
  approvingOrderId,
  page,
  onPageChange,
  onApprove,
}: ZenitPendingOrdersProps) {
  const pendingOrders = hasValidDataset && state
    ? state.productos.flatMap((product) => {
      const order = product.orden;
      return order?.estado === 'pendiente' ? [{ product, order }] : [];
    })
    : [];
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
            <li key={order.id}>
              <div>
                <strong>{product.producto}</strong>
                <span>Cantidad por definir</span>
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
