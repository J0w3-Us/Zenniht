import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Input } from '../ui/input';
import type { ZenitState } from '../../lib/zenit-api';
import { normalizeProductSearch } from './zenit-product-filters';

interface ZenitProductSearchProps {
  state: ZenitState | null;
  hasValidDataset: boolean;
  onProductSelect: (productName: string | null) => void;
}

export function ZenitProductSearch({
  state,
  hasValidDataset,
  onProductSelect,
}: ZenitProductSearchProps) {
  const [query, setQuery] = useState('');
  const matches = useMemo(() => {
    const normalizedQuery = normalizeProductSearch(query.trim());
    if (!normalizedQuery || !state?.datos_cargados || state.filas !== 4500 || state.productos.length !== 50) {
      return [];
    }
    return state.productos
      .filter((product) => normalizeProductSearch(product.producto).includes(normalizedQuery))
      .slice(0, 5);
  }, [query, state]);

  return (
    <div className="zenit-assistant-search">
      <label htmlFor="zenit-assistant-product">Consultar un producto</label>
      <div className="zenit-assistant-searchbox">
        <Search aria-hidden="true" size={16} />
        <Input
          id="zenit-assistant-product"
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.currentTarget.value);
            onProductSelect(null);
          }}
          placeholder="Nombre del producto"
          disabled={!hasValidDataset}
        />
      </div>
      {query.trim() && (
        <div className="zenit-assistant-matches" role="listbox" aria-label="Productos encontrados">
          {matches.length ? matches.map((product) => (
            <button
              key={product.producto}
              type="button"
              role="option"
              aria-selected={false}
              onClick={() => onProductSelect(product.producto)}
            >
              <span>{product.producto}</span>
              <span>{product.cuadrante_kraljic}</span>
            </button>
          )) : (
            <p role="status">
              {hasValidDataset
                ? 'No se encontró en los 50 productos.'
                : 'Carga el dataset válido de 4,500 registros para habilitar la búsqueda.'}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
