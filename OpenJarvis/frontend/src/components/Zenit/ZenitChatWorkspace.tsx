import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowRight, Bot, Calendar, CheckCircle2, Edit2, RotateCcw, Send, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import type {
  ZenitAgentOrderSummary,
  ZenitAgentStatus,
  ZenitAgentToolUse,
  ZenitProduct,
} from '../../lib/zenit-api';
import './ZenitChatWorkspace.css';

export interface ZenitChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  sources?: string[];
  tools?: ZenitAgentToolUse[];
  alerts?: ZenitProduct[];
  render_widget?: boolean;
  pendingOrders?: ZenitAgentOrderSummary[];
}

interface ZenitChatWorkspaceProps {
  messages: ZenitChatMessage[];
  agentStatus: ZenitAgentStatus | null;
  selectedModel: string;
  dateCutoff: string;
  sending: boolean;
  approvingOrderId: number | null;
  onSelectModel: (model: string) => void;
  onDateCutoffChange: (date: string) => void;
  onSendMessage: (message: string) => void;
  onApproveOrder: (orderId: number) => void;
  onOpenInventoryAlerts: () => void;
  onOpenSuggestions: (orderId?: number) => void;
}

const SUGGESTED_PROMPTS = [
  {
    title: 'Predecir desabasto a 7 días',
    subtitle: 'Qué medicamentos están en riesgo de agotarse',
    prompt: 'Ejecuta la predicción TFT para la fecha de corte actual y dime qué productos tienen alerta de desabasto.',
  },
  {
    title: 'Resumen del inventario',
    subtitle: 'Existencias actuales y prioridades Kraljic',
    prompt: 'Dame un resumen actual del inventario, cuántas unidades hay disponibles y cómo se distribuyen los cuadrantes Kraljic.',
  },
  {
    title: 'Historial de un medicamento',
    subtitle: 'Ventas recientes de Insulina glargina',
    prompt: 'Consulta el detalle y el historial de ventas de los últimos 14 días de Insulina glargina.',
  },
  {
    title: 'Sugerencias pendientes',
    subtitle: 'Órdenes de reabasto por revisar',
    prompt: 'Muéstrame las sugerencias de reabasto pendientes de aprobación.',
  },
];

export function ZenitChatWorkspace({
  messages,
  dateCutoff,
  sending,
  approvingOrderId,
  onDateCutoffChange,
  onSendMessage,
  onApproveOrder,
  onOpenInventoryAlerts,
  onOpenSuggestions,
}: ZenitChatWorkspaceProps) {
  const [input, setInput] = useState('');
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sending]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = '36px';
    if (input) {
      el.style.height = `${Math.max(36, el.scrollHeight)}px`;
    }
  }, [input]);

  const submit = () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    onSendMessage(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '36px';
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <section className="zenit-chat-workspace" aria-label="Agente ZENIT">
      <div className="zenit-chat-header-bar">
        <div className="zenit-chat-date-selector">
          <Calendar size={13} className="zenit-chat-date-icon" aria-hidden="true" />
          <span className="zenit-chat-date-label">Fecha de corte:</span>
          <input
            type="date"
            className="zenit-chat-date-input"
            value={dateCutoff}
            onChange={(e) => onDateCutoffChange(e.target.value)}
            title="Fecha de corte histórica para evaluación de inventario y predicción TFT"
          />
        </div>
      </div>
      <div className="zenit-chat-scroll">
        {messages.length === 0 ? (
          <div className="zenit-chat-welcome">
            <h2>¿Qué revisamos hoy en La Esperanza?</h2>
            <p className="zenit-chat-welcome-sub">
              Pregunta por existencias, historial de ventas, medicamentos en riesgo de agotarse
              o sugerencias de reabasto.
            </p>

            <div className="zenit-chat-suggestions">
              {SUGGESTED_PROMPTS.map((item) => (
                <button
                  key={item.title}
                  type="button"
                  className="zenit-chat-suggestion-card"
                  disabled={sending}
                  onClick={() => onSendMessage(item.prompt)}
                >
                  <strong>{item.title}</strong>
                  <span>{item.subtitle}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="zenit-chat-thread" role="log" aria-live="polite">
            {messages.map((message) => (
              <article key={message.id} className={`zenit-chat-turn is-${message.role}`}>
                {message.role === 'assistant' && (
                  <span className="zenit-chat-avatar" aria-hidden="true">
                    <Bot size={16} />
                  </span>
                )}
                <div className="zenit-chat-bubble">
                  <div className="zenit-chat-markdown">
                    {message.role === 'assistant' ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    ) : editingMessageId === message.id ? (
                      <div className="zenit-chat-inline-edit" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', width: '100%' }}>
                        <textarea
                          value={editingText}
                          onChange={(e) => setEditingText(e.target.value)}
                          rows={3}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            border: '1px solid #cbd5e1',
                            fontSize: '13px',
                            fontFamily: 'inherit',
                            resize: 'vertical',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            onClick={() => setEditingMessageId(null)}
                            style={{
                              background: 'transparent',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              padding: '3px 8px',
                              fontSize: '12px',
                              cursor: 'pointer',
                            }}
                          >
                            Cancelar
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const newText = editingText.trim();
                              setEditingMessageId(null);
                              if (newText) {
                                onSendMessage(newText);
                              }
                            }}
                            style={{
                              background: '#2563eb',
                              color: '#fff',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '3px 10px',
                              fontSize: '12px',
                              cursor: 'pointer',
                              fontWeight: 500,
                            }}
                          >
                            Guardar y Reenviar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                        <p style={{ margin: 0 }}>{message.content}</p>
                        <button
                          type="button"
                          className="zenit-chat-edit-btn"
                          title="Editar mensaje"
                          onClick={() => {
                            setEditingMessageId(message.id);
                            setEditingText(message.content);
                          }}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            padding: '2px',
                            cursor: 'pointer',
                            color: '#94a3b8',
                            opacity: 0.8,
                            flexShrink: 0,
                          }}
                        >
                          <Edit2 size={13} />
                        </button>
                      </div>
                    )}
                  </div>

                  {message.role === 'assistant' && message.render_widget === true && message.alerts && message.alerts.length > 0 && (
                    <div className="zenit-chat-evidence">
                      <div className="zenit-chat-evidence-header">
                        <strong>Riesgo de desabasto (≥ 50%)</strong>
                        <button
                          type="button"
                          className="zenit-chat-inline-link"
                          onClick={onOpenInventoryAlerts}
                        >
                          Ver en inventario
                          <ArrowRight aria-hidden="true" size={13} />
                        </button>
                      </div>
                      <ul className="zenit-chat-alert-list">
                        {message.alerts.slice(0, 6).map((alert) => (
                          <li key={alert.producto}>
                            <div>
                              <strong>{alert.producto}</strong>
                              <span>{alert.cuadrante_kraljic}</span>
                            </div>
                            <span className="zenit-chat-risk-pill">
                              {alert.probabilidad !== null
                                ? `${(alert.probabilidad * 100).toFixed(1)}%`
                                : '≥ 50%'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {message.role === 'assistant'
                    && message.pendingOrders
                    && message.pendingOrders.length > 0 && (() => {
                      const uniqueOrders = Array.from(
                        new Map(message.pendingOrders.map((o) => [o.producto, o])).values()
                      );
                      return (
                        <div className="zenit-chat-orders">
                          <div className="zenit-chat-evidence-header">
                            <strong>Sugerencias de reabasto</strong>
                            <button
                              type="button"
                              className="zenit-chat-inline-link"
                              onClick={() => onOpenSuggestions()}
                            >
                              Ver todas
                              <ArrowRight aria-hidden="true" size={13} />
                            </button>
                          </div>
                          <ul className="zenit-chat-order-list">
                            {uniqueOrders.slice(0, 5).map((order) => (
                              <li key={order.id}>
                                <div>
                                  <strong>{order.producto}</strong>
                                  <span>{order.cuadrante_kraljic} · Cantidad: Por definir</span>
                                <button
                                  type="button"
                                  className="zenit-chat-inline-link"
                                  aria-label={`Ver sugerencia para ${order.producto}`}
                                  onClick={() => onOpenSuggestions(order.id)}
                                >
                                  Ver sugerencia
                                </button>
                                </div>
                                <button
                                  type="button"
                                  className="zenit-chat-approve-btn"
                                  disabled={approvingOrderId === order.id}
                                  onClick={() => onApproveOrder(order.id)}
                                >
                                  <CheckCircle2 aria-hidden="true" size={13} />
                                  {approvingOrderId === order.id ? 'Aprobando…' : 'Aprobar'}
                                </button>
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    })()}

                  {message.role === 'assistant' && (
                    <div className="zenit-chat-actions-bar" style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', alignItems: 'center' }}>
                      <button
                        type="button"
                        className="zenit-chat-action-btn"
                        style={{ background: 'transparent', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '2px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', color: '#64748b' }}
                        title="Reintentar última consulta"
                        onClick={() => {
                          const lastUser = [...messages].reverse().find(m => m.role === 'user');
                          if (lastUser) onSendMessage(lastUser.content);
                        }}
                      >
                        <RotateCcw size={11} /> Reintentar
                      </button>
                      <button
                        type="button"
                        className="zenit-chat-action-btn"
                        style={{ background: 'transparent', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '2px 6px', fontSize: '11px', display: 'flex', alignItems: 'center', cursor: 'pointer', color: '#64748b' }}
                        title="Respuesta útil"
                        onClick={(e) => {
                          (e.currentTarget as HTMLElement).style.color = '#16a34a';
                        }}
                      >
                        <ThumbsUp size={11} />
                      </button>
                      <button
                        type="button"
                        className="zenit-chat-action-btn"
                        style={{ background: 'transparent', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '2px 6px', fontSize: '11px', display: 'flex', alignItems: 'center', cursor: 'pointer', color: '#64748b' }}
                        title="Respuesta con errores"
                        onClick={(e) => {
                          (e.currentTarget as HTMLElement).style.color = '#dc2626';
                        }}
                      >
                        <ThumbsDown size={11} />
                      </button>
                    </div>
                  )}
                </div>
              </article>
            ))}

            <AnimatePresence>
            {sending && (
              <motion.article
                className="zenit-chat-turn is-assistant is-thinking"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
              >
                <span className="zenit-chat-avatar" aria-hidden="true">
                  <Bot size={16} />
                </span>
                <div className="zenit-chat-bubble">
                  <span className="zenit-chat-thinking-dots" aria-label="Analizando" role="status">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="zenit-thinking-dot"
                        animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
                        transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.18, ease: 'easeInOut' }}
                      />
                    ))}
                  </span>
                  <p className="zenit-chat-thinking-text">Analizando…</p>
                </div>
              </motion.article>
            )}
            </AnimatePresence>
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="zenit-chat-composer-wrap">
        <form
          className="zenit-chat-composer"
          onSubmit={handleSubmit}
          onClick={() => textareaRef.current?.focus()}
        >
          <label htmlFor="zenit-agent-input" className="sr-only">
            Pregunta al agente ZENIT
          </label>
          <textarea
            ref={textareaRef}
            id="zenit-agent-input"
            rows={1}
            value={input}
            onChange={(event) => setInput(event.currentTarget.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje para consultar el inventario o predecir desabasto…"
            disabled={sending}
          />
          <button
            type="submit"
            className="zenit-chat-send-btn"
            aria-label="Enviar consulta"
            disabled={!input.trim() || sending}
          >
            <Send aria-hidden="true" size={16} />
          </button>
        </form>
      </div>
    </section>
  );
}
