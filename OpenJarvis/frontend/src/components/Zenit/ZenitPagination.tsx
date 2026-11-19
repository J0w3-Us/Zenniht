import { ChevronLeft, ChevronRight } from 'lucide-react';
import './ZenitPagination.css';

export const ZENIT_PAGE_SIZE = 20;

export interface PaginatedItems<T> {
  items: T[];
  page: number;
  pageCount: number;
}

export function paginateItems<T>(
  items: readonly T[],
  requestedPage: number,
): PaginatedItems<T> {
  const pageCount = Math.max(1, Math.ceil(items.length / ZENIT_PAGE_SIZE));
  const validPage = Number.isInteger(requestedPage) ? requestedPage : 1;
  const page = Math.min(Math.max(1, validPage), pageCount);
  const start = (page - 1) * ZENIT_PAGE_SIZE;

  return {
    items: items.slice(start, start + ZENIT_PAGE_SIZE),
    page,
    pageCount,
  };
}

interface ZenitPaginationProps {
  label: string;
  page: number;
  totalItems: number;
  onPageChange: (page: number) => void;
}

export function ZenitPagination({
  label,
  page,
  totalItems,
  onPageChange,
}: ZenitPaginationProps) {
  const pageCount = Math.max(1, Math.ceil(totalItems / ZENIT_PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, page), pageCount);
  if (pageCount <= 1) return null;

  const firstItem = (currentPage - 1) * ZENIT_PAGE_SIZE + 1;
  const lastItem = Math.min(currentPage * ZENIT_PAGE_SIZE, totalItems);

  return (
    <nav className="zenit-pagination" aria-label={`Paginación de ${label}`}>
      <span className="zenit-pagination-range" aria-live="polite">
        Mostrando {firstItem} a {lastItem} de {totalItems}
      </span>
      <div className="zenit-pagination-controls">
        <button
          type="button"
          className="zenit-pagination-button"
          aria-label={`Página anterior de ${label}`}
          disabled={currentPage === 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ChevronLeft aria-hidden="true" size={16} />
          Anterior
        </button>
        <span className="zenit-pagination-current" aria-current="page">
          Página {currentPage} de {pageCount}
        </span>
        <button
          type="button"
          className="zenit-pagination-button"
          aria-label={`Página siguiente de ${label}`}
          disabled={currentPage === pageCount}
          onClick={() => onPageChange(currentPage + 1)}
        >
          Siguiente
          <ChevronRight aria-hidden="true" size={16} />
        </button>
      </div>
    </nav>
  );
}
