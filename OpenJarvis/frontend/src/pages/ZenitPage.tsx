import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { isTauri } from '@tauri-apps/api/core';
import {
  AlertTriangle,
  Database,
  MessageSquare,
  PackageSearch,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ShoppingBasket,
  Trash2,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import {
  ZenitChatWorkspace,
  type ZenitChatMessage,
} from '../components/Zenit/ZenitChatWorkspace';
import { ZenitProductSearch } from '../components/Zenit/ZenitProductSearch';
import { ZenitSuggestionsPage } from '../components/Zenit/ZenitSuggestionsPage';
import { ZenitToasts, type ZenitToastItem } from '../components/Zenit/ZenitToasts';
import { InventoryTable } from '../components/Zenit/InventoryTable';
import { paginateItems, ZenitPagination } from '../components/Zenit/ZenitPagination';
import {
  getVisibleZenitProducts,
  type ZenitProductFilter,
} from '../components/Zenit/zenit-product-filters';
import {
  approveZenitOrder,
  getZenitAgentStatus,
  getZenitStartupError,
  getZenitState,
  loadZenitCanonicalDataset,
  sendZenitAgentMessage,
  uploadZenitDataset,
  type ZenitAgentStatus,
  type ZenitState,
} from '../lib/zenit-api';
import './ZenitPage.css';
import { getChatSuggestionIds, getPendingSuggestions, getSuggestionPage } from '../components/Zenit/zenit-suggestions';

const FECHA_DEMO = '2026-10-22';
const CHAT_SESSIONS_KEY = 'zenit-chat-sessions-v1';
type ZenitScreen = 'chat' | 'inventory' | 'suggestions';

interface ZenitChatSession {
  id: string;
  title: string;
  messages: ZenitChatMessage[];
}

function loadStoredSessions(): ZenitChatSession[] {
  try {
    const raw = window.localStorage.getItem(CHAT_SESSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as ZenitChatSession[]) : [];
  } catch {
    return [];
  }
}

const SCREEN_COPY: Record<ZenitScreen, { title: string; description: string }> = {
  chat: {
    title: 'Asistente de inventario',
    description: 'Consulta existencias, predicciones de desabasto y sugerencias de reabasto.',
  },
  inventory: {
    title: 'Inventario',
    description: 'Revisa los 50 productos, alertas de desabasto y prioridad Kraljic.',
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
  const [approvingOrderId, setApprovingOrderId] = useState<number | null>(null);
  const [toasts, setToasts] = useState<ZenitToastItem[]>([]);
  const [productFilter, setProductFilter] = useState<ZenitProductFilter>('all');
  const [sortByRisk, setSortByRisk] = useState(false);
  const [selectedProductName, setSelectedProductName] = useState<string | null>(null);
  const [activeScreen, setActiveScreen] = useState<ZenitScreen>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inventoryPage, setInventoryPage] = useState(1);
  const [suggestionsPage, setSuggestionsPage] = useState(1);
  const [highlightedOrderIds, setHighlightedOrderIds] = useState<number[]>([]);
  const [agentStatus, setAgentStatus] = useState<ZenitAgentStatus | null>(null);
  const [selectedModel, setSelectedModel] = useState('');
  const [sendingChat, setSendingChat] = useState(false);
  const [sessions, setSessions] = useState<ZenitChatSession[]>(() => loadStoredSessions());
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    const initial = loadStoredSessions();
    return initial[0]?.id ?? null;
  });
  const nextChatId = useRef(Date.now());
  const nextToastId = useRef(1);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );
  const chatMessages = useMemo(() => {
    const messages = activeSession?.messages ?? [];
    if (!state) return messages;
    const pendingIds = new Set(getPendingSuggestions(state).map((p) => p.order.id));
    return messages.map((message) => ({ ...message,
      pendingOrders: message.pendingOrders?.filter((o) => pendingIds.has(o.id)),
    }));
  }, [activeSession, state]);

  useEffect(() => {
    try {
      window.localStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(sessions));
    } catch {
      // Ignore storage quota errors.
    }
  }, [sessions]);

  const pushToast = useCallback(
    (
      message: string,
      tone: 'error' | 'warning' = 'error',
      action?: { label: string; onAction: () => void },
    ) => {
      const id = nextToastId.current++;
      setToasts((current) => [
        ...current.filter((item) => item.message !== message),
        {
          id,
          message,
          tone,
          actionLabel: action?.label,
          onAction: action?.onAction,
        },
      ]);
    },
    [],
  );

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const refreshAgentStatus = useCallback(
    async (model?: string) => {
      try {
        const status = await getZenitAgentStatus(model);
        setAgentStatus(status);
        if (status.modelo_activo) {
          setSelectedModel((current) => current || status.modelo_activo || '');
        } else {
          pushToast(
            status.detalle || 'El asistente local no tiene un modelo listo en Ollama.',
            'warning',
          );
        }
      } catch {
        setAgentStatus({
          ollama_disponible: false,
          url: 'http://127.0.0.1:11434',
          modelos: [],
          modelo_activo: null,
          detalle: 'No se pudo conectar con el servicio del asistente.',
        });
        pushToast('No se pudo verificar la conexión con el asistente local.', 'warning');
      }
    },
    [pushToast],
  );

  const refreshState = useCallback(async () => {
    setLoading(true);
    try {
      const startupError = await getZenitStartupError();
      if (startupError) throw new Error(startupError);
      let currentState = await getZenitState();
      if (!currentState.datos_cargados) {
        await loadZenitCanonicalDataset();
        currentState = await getZenitState();
      }
      setState(currentState);
    } catch (requestError) {
      pushToast(getErrorMessage(requestError), 'error');
    } finally {
      setLoading(false);
    }
  }, [pushToast]);

  useEffect(() => {
    void refreshState();
    void refreshAgentStatus();
  }, [refreshState, refreshAgentStatus]);

  const handleSendChat = async (messageText: string) => {
    const userMessage: ZenitChatMessage = {
      id: nextChatId.current++,
      role: 'user',
      content: messageText,
    };
    const historyPayload = chatMessages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    const sessionId = activeSessionId ?? `chat-${Date.now()}`;
    const shortTitle = messageText.length > 34 ? `${messageText.slice(0, 34)}…` : messageText;

    setActiveSessionId(sessionId);
    setSessions((current) => {
      const exists = current.some((s) => s.id === sessionId);
      if (!exists) {
        return [{ id: sessionId, title: shortTitle, messages: [userMessage] }, ...current];
      }
      return current.map((s) =>
        s.id === sessionId ? { ...s, messages: [...s.messages, userMessage] } : s,
      );
    });
    setSendingChat(true);

    try {
      const reply = await sendZenitAgentMessage({
        mensaje: messageText,
        historial: historyPayload,
        modelo: selectedModel || agentStatus?.modelo_activo || undefined,
        fecha_corte: dateCutoff,
      });
      if (reply.estado_actualizado) {
        setState(reply.estado_actualizado);
      }
      const mentionedIds = getChatSuggestionIds(reply);
      if (reply.herramientas_usadas.length > 0) {
        setHighlightedOrderIds(mentionedIds);
        setSuggestionsPage(1);
      }
      const assistantMessage: ZenitChatMessage = {
        id: nextChatId.current++,
        role: 'assistant',
        content: reply.respuesta,
        model: reply.modelo,
        sources: reply.fuentes,
        tools: reply.herramientas_usadas,
        alerts: reply.alertas.length > 0 && (reply.mostrar_alertas ?? reply.herramientas_usadas.some(
          (t) => (
            t.nombre === 'ejecutar_prediccion_tft'
            || t.nombre === 'consultar_resumen_inventario'
            || t.nombre === 'listar_productos_por_filtro'
          ),
        ))
          ? reply.alertas
          : undefined,
        pendingOrders: mentionedIds.length > 0
          ? reply.ordenes_pendientes.filter((o) => mentionedIds.includes(o.id))
          : undefined,
      };
      setSessions((current) =>
        current.map((s) =>
          s.id === sessionId ? { ...s, messages: [...s.messages, assistantMessage] } : s,
        ),
      );
    } catch (requestError) {
      pushToast(getErrorMessage(requestError), 'error', {
        label: 'Reintentar',
        onAction: () => void refreshAgentStatus(selectedModel || undefined),
      });
    } finally {
      setSendingChat(false);
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setActiveScreen('chat');
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setActiveScreen('chat');
  };

  const handleDeleteSession = (sessionId: string) => {
    setSessions((current) => {
      const remaining = current.filter((s) => s.id !== sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(remaining[0]?.id ?? null);
      }
      return remaining;
    });
  };

  useEffect(() => {
    contentElement.current?.scrollTo({ top: 0 });
  }, [activeScreen]);

  const handleUpload = async (file?: File) => {
    if (!file) return;
    setUploading(true);
    try {
      await uploadZenitDataset(file);
      setState(await getZenitState());
      setProductFilter('all');
      setSortByRisk(false);
      setSelectedProductName(null);
      setInventoryPage(1);
      setSuggestionsPage(1);
    } catch (requestError) {
      pushToast(getErrorMessage(requestError), 'error');
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
    try {
      await loadZenitCanonicalDataset();
      setState(await getZenitState());
      setProductFilter('all');
      setSortByRisk(false);
      setSelectedProductName(null);
      setInventoryPage(1);
      setSuggestionsPage(1);
    } catch (requestError) {
      pushToast(getErrorMessage(requestError), 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleApprove = async (orderId: number) => {
    setApprovingOrderId(orderId);
    try {
      await approveZenitOrder(orderId);
      setState(await getZenitState());
    } catch (requestError) {
      pushToast(getErrorMessage(requestError), 'error');
    } finally {
      setApprovingOrderId(null);
    }
  };

  const products = state?.productos ?? [];
  const pendingSuggestions = getPendingSuggestions(state);
  const mentionedPendingCount = pendingSuggestions.filter((p) => highlightedOrderIds.includes(p.order.id)).length;
  const handleOpenSuggestions = (orderId?: number) => {
    const ids = orderId === undefined ? highlightedOrderIds : [orderId];
    if (orderId !== undefined) setHighlightedOrderIds(ids);
    setSuggestionsPage(orderId === undefined ? 1 : getSuggestionPage(state, orderId, ids));
    setActiveScreen('suggestions');
  };
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
      <div className={`zenit-shell${sidebarOpen ? '' : ' is-sidebar-collapsed'}`}>
        <input
          ref={fileInput}
          id="zenit-csv"
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(event) => void handleUpload(event.currentTarget.files?.[0])}
          disabled={uploading}
        />
        <aside
          className="zenit-sidebar"
          aria-label="Navegación principal"
          aria-hidden={!sidebarOpen}
        >
          <div className="zenit-brand-row">
            <div className="zenit-brand" aria-label="ZENIT para La Esperanza">
              <span className="zenit-brand-mark"><Database aria-hidden="true" size={18} /></span>
              <span className="zenit-brand-copy">
                <strong>ZENIT</strong>
                <span>La Esperanza</span>
              </span>
            </div>
            <button
              type="button"
              className="zenit-sidebar-toggle"
              aria-label="Cerrar barra lateral"
              title="Ocultar barra lateral"
              onClick={() => setSidebarOpen(false)}
            >
              <PanelLeftClose aria-hidden="true" size={17} />
            </button>
          </div>
          <nav className="zenit-nav" aria-label="Pantallas">
            <button
              type="button"
              className="zenit-new-chat-btn"
              onClick={handleNewChat}
            >
              <Plus aria-hidden="true" size={16} />
              Nueva consulta
            </button>

            {sessions.length > 0 && (
              <div className="zenit-chat-history">
                <p className="zenit-nav-label">Conversaciones</p>
                <ul className="zenit-chat-history-list">
                  {sessions.map((session) => {
                    const isActive = activeScreen === 'chat' && activeSessionId === session.id;
                    return (
                      <li key={session.id} className={`zenit-chat-history-item${isActive ? ' is-active' : ''}`}>
                        <button
                          type="button"
                          className="zenit-chat-history-btn"
                          onClick={() => handleSelectSession(session.id)}
                          title={session.title}
                        >
                          <MessageSquare aria-hidden="true" size={14} />
                          <span>{session.title}</span>
                        </button>
                        <button
                          type="button"
                          className="zenit-chat-history-delete"
                          aria-label={`Eliminar conversación ${session.title}`}
                          onClick={() => handleDeleteSession(session.id)}
                        >
                          <Trash2 aria-hidden="true" size={13} />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            <div className="zenit-nav-section">
              <p className="zenit-nav-label">Menú</p>
              <button
                type="button"
                className="zenit-nav-link"
                aria-current={activeScreen === 'chat' ? 'page' : undefined}
                onClick={() => setActiveScreen('chat')}
              >
                <MessageSquare aria-hidden="true" size={17} />
                Agente ZENIT
              </button>
              <button
                type="button"
                className="zenit-nav-link"
                aria-current={activeScreen === 'inventory' ? 'page' : undefined}
                onClick={() => setActiveScreen('inventory')}
              >
                <PackageSearch aria-hidden="true" size={17} />
                Inventario (50)
              </button>
              <button
                type="button"
                className="zenit-nav-link"
                aria-current={activeScreen === 'suggestions' ? 'page' : undefined}
                onClick={() => handleOpenSuggestions()}
              >
                <ShoppingBasket aria-hidden="true" size={17} />
                Sugerencias
                {pendingSuggestions.length > 0 && (
                  <span className={`zenit-nav-badge${mentionedPendingCount > 0 ? ' is-mentioned' : ''}`}
                    aria-label={`${pendingSuggestions.length} pendientes; ${mentionedPendingCount} mencionadas en el chat`}>
                    {pendingSuggestions.length}
                  </span>
                )}
              </button>
            </div>
          </nav>
        </aside>

        <div className="zenit-main">
          <header className="zenit-header">
            <div className="zenit-header-left">
              {!sidebarOpen && (
                <button
                  type="button"
                  className="zenit-sidebar-toggle is-header"
                  aria-label="Abrir barra lateral"
                  title="Mostrar barra lateral"
                  onClick={() => setSidebarOpen(true)}
                >
                  <PanelLeftOpen aria-hidden="true" size={18} />
                </button>
              )}
              <div className="zenit-header-copy">
                <h1 className="zenit-title">{SCREEN_COPY[activeScreen].title}</h1>
                <p className="zenit-lead">{SCREEN_COPY[activeScreen].description}</p>
              </div>
            </div>
          </header>

          <div
            ref={contentElement}
            className={`zenit-content${activeScreen === 'chat' ? ' is-chat' : ''}`}
            id="zenit-main-content"
            tabIndex={-1}
          >
            <ZenitToasts toasts={toasts} onDismiss={dismissToast} />

            {activeScreen === 'chat' && (
              <ZenitChatWorkspace
                messages={chatMessages}
                agentStatus={agentStatus}
                selectedModel={selectedModel}
                dateCutoff={dateCutoff}
                sending={sendingChat}
                approvingOrderId={approvingOrderId}
                onSelectModel={setSelectedModel}
                onDateCutoffChange={setDateCutoff}
                onSendMessage={(msg) => void handleSendChat(msg)}
                onApproveOrder={(orderId) => void handleApprove(orderId)}
                onOpenInventoryAlerts={() => handleFilterChange('risk')}
                onOpenSuggestions={handleOpenSuggestions}
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
                    <Button type="button" className="zenit-primary-action" onClick={() => void handleLoadDataset()}>
                      Cargar dataset
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
                        <span>Sin predicción TFT. Pídele al Agente ZENIT que ejecute la predicción para ver riesgos.</span>
                      </div>
                    )}
                    <p className="zenit-table-hint">Desliza la tabla horizontalmente para consultar todas las columnas.</p>
                    <div className="zenit-table-frame">
                      <InventoryTable
                        products={paginatedProducts.items}
                        stockDate={state?.fecha_existencia ?? null}
                        approvingOrderId={approvingOrderId}
                        actionsDisabled={uploading || loading}
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
                busy={loading || uploading}
                approvingOrderId={approvingOrderId}
                page={suggestionsPage}
                onPageChange={setSuggestionsPage}
                onApprove={(orderId) => void handleApprove(orderId)}
                highlightedOrderIds={highlightedOrderIds}
              />
            )}
          </div>
        </div>
      </div>
    </main>
    </>
  );
}
