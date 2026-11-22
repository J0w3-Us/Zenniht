import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { ZenitChatWorkspace, type ZenitChatMessage } from './ZenitChatWorkspace';

const baseProps = {
  selectedModel: 'qwen2.5:3b',
  dateCutoff: '2026-10-22',
  sending: false,
  approvingOrderId: null,
  onSelectModel: vi.fn(),
  onDateCutoffChange: vi.fn(),
  onSendMessage: vi.fn(),
  onApproveOrder: vi.fn(),
  onOpenInventoryAlerts: vi.fn(),
  onOpenSuggestions: vi.fn(),
};

describe('ZenitChatWorkspace', () => {
  it('muestra la bienvenida tipo chat sin etiquetas de estado de conexión', () => {
    const html = renderToStaticMarkup(
      <ZenitChatWorkspace
        {...baseProps}
        messages={[]}
        agentStatus={{
          ollama_disponible: true,
          url: 'http://127.0.0.1:11434',
          modelos: ['qwen2.5:3b'],
          modelo_activo: 'qwen2.5:3b',
          detalle: 'Ollama local conectado (qwen2.5:3b).',
        }}
      />,
    );

    expect(html).toContain('¿Qué revisamos hoy en La Esperanza?');
    expect(html).toContain('Predecir desabasto a 7 días');
    expect(html).not.toContain('Ollama');
    expect(html).not.toContain('SQLite');
    expect(html).not.toContain('100% local');
  });

  it('renderiza alertas y sugerencias sin badges técnicos de fuente o herramienta', () => {
    const messages: ZenitChatMessage[] = [
      { id: 1, role: 'user', content: 'Muéstrame las sugerencias pendientes' },
      {
        id: 2,
        role: 'assistant',
        content: 'Hay 1 sugerencia pendiente.',
        sources: ['TFT LOCAL'],
        tools: [{ nombre: 'consultar_sugerencias_pendientes', fuente: 'SQLITE LOCAL' }],
        alerts: [
          {
            producto: 'Insulina glargina',
            cuadrante_kraljic: 'Estratégico',
            existencia: 0,
            probabilidad: 1,
            en_desabasto: true,
            orden: { id: 7, estado: 'pendiente', cantidad_sugerida: null },
          },
        ],
        pendingOrders: [
          {
            id: 7,
            producto: 'Insulina glargina',
            cuadrante_kraljic: 'Estratégico',
            probabilidad_desabasto: 1,
            estado: 'pendiente',
            cantidad_sugerida: null,
            fecha_corte: '2026-10-22',
          },
        ],
      },
    ];

    const html = renderToStaticMarkup(
      <ZenitChatWorkspace {...baseProps} messages={messages} agentStatus={null} />,
    );

    expect(html).toContain('Insulina glargina');
    expect(html).toContain('100.0%');
    expect(html).toContain('Cantidad: Por definir');
    expect(html).toContain('Aprobar');
    expect(html).not.toContain('TFT LOCAL');
    expect(html).not.toContain('consultar_sugerencias_pendientes');
  });
});
