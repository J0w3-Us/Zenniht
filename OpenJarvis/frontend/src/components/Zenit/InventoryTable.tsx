import { Check, CircleAlert, CircleHelp, LoaderCircle } from 'lucide-react';
import type { ZenitProduct } from '../../lib/zenit-api';

interface InventoryTableProps {
  products: ZenitProduct[];
  stockDate: string | null;
  approvingOrderId: number | null;
  actionsDisabled: boolean;
  onApprove: (orderId: number) => void;
}

function ProductStatus({ product }: { product: ZenitProduct }) {
  if (product.en_desabasto === null || product.probabilidad === null) {
    return (
      <span className="zenit-status zenit-status-unknown">
        <CircleHelp aria-hidden="true" size={15} />
        Sin predicción
      </span>
    );
  }

  if (product.en_desabasto) {
    return (
      <span className="zenit-status zenit-status-risk">
        <CircleAlert aria-hidden="true" size={14} />
        Riesgo de desabasto
      </span>
    );
  }

  return (
    <span className="zenit-status zenit-status-clear">
      <Check aria-hidden="true" size={15} />
      Sin alerta
    </span>
  );
}

function RiskIndicator({ product }: { product: ZenitProduct }) {
  if (product.probabilidad === null) {
    return <span className="zenit-risk-unknown">—</span>;
  }

  const probability = Math.max(0, Math.min(1, product.probabilidad));
  const percent = probability * 100;
  const isAlert = product.en_desabasto === true && probability >= 0.5;

  return (
    <div className={`zenit-risk-indicator${isAlert ? ' is-alert' : ''}`}>
      <span className="zenit-risk-percent">{percent.toFixed(1)}%</span>
      <span
        className="zenit-risk-track"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Number(percent.toFixed(1))}
        aria-label={`Riesgo TFT a 7 días: ${percent.toFixed(1)}%`}
      >
        <span className="zenit-risk-fill" style={{ width: `${percent}%` }} />
      </span>
    </div>
  );
}

function OrderStatus({
  product,
  approvingOrderId,
  actionsDisabled,
  onApprove,
}: Pick<InventoryTableProps, 'approvingOrderId' | 'actionsDisabled' | 'onApprove'> & {
  product: ZenitProduct;
}) {
  const order = product.orden;
  if (!order) return <span className="zenit-order-empty">—</span>;

  if (order.estado === 'aprobada') {
    return (
      <span className="zenit-order-approved">
        <Check aria-hidden="true" size={15} />
        Aprobada
      </span>
    );
  }

  const isApproving = approvingOrderId === order.id;
  const isDisabled = actionsDisabled || approvingOrderId !== null;
  return (
    <div className="zenit-order-pending">
      <span className="zenit-order-state">Pendiente</span>
      <span
        className="zenit-order-tooltip"
        title="Regla de reabasto pendiente de acuerdo"
      >
        <button
          type="button"
          className="zenit-order-quantity"
          aria-label="Cantidad por definir. Regla de reabasto pendiente de acuerdo."
          disabled
        >
          Cantidad por definir
        </button>
      </span>
      <button
        type="button"
        disabled={isDisabled}
        onClick={() => onApprove(order.id)}
        className="zenit-approve-button"
        aria-label={`Aprobar sugerencia para ${product.producto}`}
      >
        {isApproving && <LoaderCircle aria-hidden="true" size={14} className="animate-spin" />}
        Aprobar sugerencia
      </button>
    </div>
  );
}

export function InventoryTable({
  products,
  stockDate,
  approvingOrderId,
  actionsDisabled,
  onApprove,
}: InventoryTableProps) {
  return (
    <div
      className="zenit-table-scroll"
      role="region"
      aria-label="Tabla de productos, desplázate horizontalmente para ver todas las columnas"
      tabIndex={0}
    >
      <table className="zenit-inventory-table">
        <caption className="sr-only">
          Existencias del {stockDate ?? 'último corte disponible'} y predicción TFT de desabasto a siete días
          para {products.length} productos de La Esperanza
        </caption>
        <thead>
          <tr>
            <th scope="col">Producto</th>
            <th scope="col">
              Existencia
              {stockDate && <span className="zenit-stock-date">al {stockDate}</span>}
            </th>
            <th scope="col">Kraljic</th>
            <th scope="col">Riesgo a 7 días</th>
            <th scope="col">Estado</th>
            <th scope="col">Sugerencia</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const isAlert = product.en_desabasto === true;
            return (
              <tr key={product.producto} className={isAlert ? 'is-alert' : undefined}>
                <th scope="row" className="zenit-product-name">
                  {product.producto}
                </th>
                <td className="zenit-stock-cell">
                  {typeof product.existencia === 'number' && Number.isFinite(product.existencia)
                    ? product.existencia.toLocaleString('es-MX')
                    : '—'}
                </td>
                <td>
                  <span className="zenit-kraljic" data-quadrant={product.cuadrante_kraljic}>
                    {product.cuadrante_kraljic}
                  </span>
                </td>
                <td className="zenit-risk-cell">
                  <RiskIndicator product={product} />
                </td>
                <td>
                  <ProductStatus product={product} />
                </td>
                <td>
                  <OrderStatus
                    product={product}
                    approvingOrderId={approvingOrderId}
                    actionsDisabled={actionsDisabled}
                    onApprove={onApprove}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
