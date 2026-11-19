import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { ZenitLocalCopilot } from './ZenitLocalCopilot';

describe('ZenitLocalCopilot', () => {
  it('inicia como una burbuja y no muestra una paleta de comandos', () => {
    const html = renderToStaticMarkup(
      <ZenitLocalCopilot
        state={null}
        busy={false}
        onLoadDataset={vi.fn()}
        onPredict={vi.fn()}
        onOpenScreen={vi.fn()}
        onFilterChange={vi.fn()}
        onProductSelect={vi.fn()}
      />,
    );

    expect(html).toContain('aria-label="Abrir copiloto local"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain('role="dialog"');
    expect(html).not.toContain('Comandos disponibles');
  });
});
