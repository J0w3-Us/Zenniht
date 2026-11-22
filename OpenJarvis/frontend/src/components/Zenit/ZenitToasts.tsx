import { useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

export interface ZenitToastItem {
  id: number;
  message: string;
  tone: 'error' | 'warning';
  actionLabel?: string;
  onAction?: () => void;
}

const TOAST_DURATION_MS = 6000;

function ZenitToastCard({
  toast,
  onDismiss,
}: {
  toast: ZenitToastItem;
  onDismiss: (id: number) => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(toast.id), TOAST_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div className={`zenit-toast is-${toast.tone}`} role="alert">
      <AlertTriangle aria-hidden="true" size={16} />
      <p>{toast.message}</p>
      {toast.actionLabel && toast.onAction && (
        <button
          type="button"
          className="zenit-toast-action"
          onClick={() => {
            toast.onAction?.();
            onDismiss(toast.id);
          }}
        >
          {toast.actionLabel}
        </button>
      )}
      <button
        type="button"
        className="zenit-toast-close"
        aria-label="Cerrar aviso"
        onClick={() => onDismiss(toast.id)}
      >
        <X aria-hidden="true" size={14} />
      </button>
    </div>
  );
}

export function ZenitToasts({
  toasts,
  onDismiss,
}: {
  toasts: ZenitToastItem[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div className="zenit-toasts" aria-live="assertive">
      {toasts.map((toast) => (
        <ZenitToastCard key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
