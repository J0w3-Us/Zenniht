import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  ArrowRight,
  Bot,
  Database,
  Send,
  X,
} from 'lucide-react';
import type { ZenitState } from '../../lib/zenit-api';
import type { ZenitProductFilter } from './zenit-product-filters';
import {
  resolveZenitLocalQuery,
  type ZenitCopilotAction,
} from './zenit-local-copilot';
import './ZenitLocalCopilot.css';

type ZenitScreen = 'overview' | 'inventory' | 'suggestions';
type QuickFilter = Exclude<ZenitProductFilter, 'search'>;

interface ZenitLocalCopilotProps {
  state: ZenitState | null;
  busy: boolean;
  onLoadDataset: () => void;
  onPredict: () => void;
  onOpenScreen: (screen: ZenitScreen) => void;
  onFilterChange: (filter: QuickFilter) => void;
  onProductSelect: (productName: string | null) => void;
}

interface CopilotMessage {
  id: number;
  role: 'assistant' | 'user';
  text: string;
  action?: ZenitCopilotAction;
  actionLabel?: string;
}

const INITIAL_MESSAGE: CopilotMessage = {
  id: 0,
  role: 'assistant',
  text: 'Puedo consultar las existencias, los productos y las alertas TFT de esta sesión. Mis respuestas se limitan a datos locales de ZENIT.',
};

function isValidDataset(state: ZenitState | null): boolean {
  return Boolean(
    state?.datos_cargados && state.filas === 4500 && state.productos.length === 50,
  );
}

export function ZenitLocalCopilot({
  state,
  busy,
  onLoadDataset,
  onPredict,
  onOpenScreen,
  onFilterChange,
  onProductSelect,
}: ZenitLocalCopilotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<CopilotMessage[]>([INITIAL_MESSAGE]);
  const nextMessageId = useRef(1);
  const launcher = useRef<HTMLButtonElement>(null);
  const queryInput = useRef<HTMLInputElement>(null);
  const transcriptEnd = useRef<HTMLDivElement>(null);
  const datasetIsValid = isValidDataset(state);

  useEffect(() => {
    if (!isOpen) return;
    queryInput.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
        launcher.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) transcriptEnd.current?.scrollIntoView({ block: 'end' });
  }, [isOpen, messages]);

  const runQuery = (value: string) => {
    const trimmedQuery = value.trim();
    if (!trimmedQuery) return;

    const reply = resolveZenitLocalQuery(trimmedQuery, state);
    setMessages((current) => [
      ...current,
      {
        id: nextMessageId.current++,
        role: 'user',
        text: trimmedQuery,
      },
      {
        id: nextMessageId.current++,
        role: 'assistant',
        text: reply.text,
        action: reply.action,
        actionLabel: reply.actionLabel,
      },
    ]);
    setQuery('');
  };

  const runAction = (action: ZenitCopilotAction) => {
    switch (action.type) {
      case 'load':
        if (!busy) onLoadDataset();
        return;
      case 'predict':
        if (datasetIsValid && !busy) onPredict();
        return;
      case 'overview':
        onOpenScreen('overview');
        return;
      case 'suggestions':
        onOpenScreen('suggestions');
        return;
      case 'inventory':
        if (action.productName) {
          onProductSelect(action.productName);
        } else {
          onFilterChange(action.filter);
          onOpenScreen('inventory');
        }
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    runQuery(query);
  };

  return (
    <aside className="zenit-copilot" aria-label="Copiloto local de inventario">
      {isOpen && (
        <section
          id="zenit-copilot-panel"
          className="zenit-copilot-panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="zenit-copilot-title"
        >
          <header className="zenit-copilot-header">
            <span className="zenit-copilot-mark" aria-hidden="true">
              <Bot size={18} />
            </span>
            <div className="zenit-copilot-heading">
              <h2 id="zenit-copilot-title">Copiloto local</h2>
              <p>Consultas sobre inventario y desabasto</p>
            </div>
            <button
              type="button"
              className="zenit-copilot-close"
              aria-label="Cerrar copiloto"
              onClick={() => {
                setIsOpen(false);
                launcher.current?.focus();
              }}
            >
              <X aria-hidden="true" size={17} />
            </button>
          </header>

          <div className="zenit-copilot-context" aria-label="Contexto disponible">
            <span>
              <Database aria-hidden="true" size={14} />
              {datasetIsValid ? '4,500 filas · 50 productos' : 'Dataset pendiente'}
            </span>
            {state?.fecha_existencia && (
              <span>Existencias al {state.fecha_existencia}</span>
            )}
          </div>

          <div className="zenit-copilot-conversation">
            <div
              className="zenit-copilot-transcript"
              role="log"
              aria-label="Conversación local con ZENIT"
              aria-live="polite"
              aria-relevant="additions text"
            >
              {messages.map((message) => {
                const action = message.action;
                return (
                  <article
                    key={message.id}
                    className={`zenit-copilot-message is-${message.role}`}
                  >
                    {message.role === 'assistant' && (
                      <span className="zenit-copilot-message-mark" aria-hidden="true">
                        <Bot size={14} />
                      </span>
                    )}
                    <div className="zenit-copilot-message-content">
                      <p>{message.text}</p>
                      {action && message.actionLabel && (
                        <button
                          type="button"
                          className="zenit-copilot-reply-action"
                          disabled={
                            (action.type === 'load' && busy)
                            || (action.type === 'predict' && (!datasetIsValid || busy))
                          }
                          onClick={() => runAction(action)}
                        >
                          {message.actionLabel}
                          <ArrowRight aria-hidden="true" size={14} />
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
              <div ref={transcriptEnd} />
            </div>
          </div>

          <form className="zenit-copilot-composer" onSubmit={handleSubmit}>
            <label htmlFor="zenit-copilot-query">Pregunta</label>
            <div className="zenit-copilot-input-row">
              <input
                ref={queryInput}
                id="zenit-copilot-query"
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
                placeholder="Stock, producto, alertas…"
                autoComplete="off"
              />
              <button
                type="submit"
                aria-label="Enviar pregunta local"
                disabled={!query.trim()}
              >
                <Send aria-hidden="true" size={16} />
              </button>
            </div>
            <p>Respuestas limitadas a datos locales; sin LLM.</p>
          </form>
        </section>
      )}

      <button
        ref={launcher}
        type="button"
        className={`zenit-copilot-launcher${isOpen ? ' is-open' : ''}`}
        aria-label={isOpen ? 'Cerrar copiloto local' : 'Abrir copiloto local'}
        aria-expanded={isOpen}
        aria-controls={isOpen ? 'zenit-copilot-panel' : undefined}
        onClick={() => setIsOpen((open) => !open)}
      >
        {isOpen ? <X aria-hidden="true" size={20} /> : <Bot aria-hidden="true" size={21} />}
        <span>Copiloto</span>
      </button>
    </aside>
  );
}
