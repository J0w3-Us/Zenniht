import { invoke, isTauri } from '@tauri-apps/api/core';


export interface ZenitOrder {
  id: number;
  estado: 'pendiente' | 'aprobada';
  cantidad_sugerida: number | null;
}

export interface ZenitProduct {
  producto: string;
  cuadrante_kraljic: string;
  /** Existencia observada en la fecha del último corte local. */
  existencia?: number | null;
  probabilidad: number | null;
  en_desabasto: boolean | null;
  orden: ZenitOrder | null;
}

export interface ZenitState {
  datos_cargados: boolean;
  filas: number;
  /** Última fecha registrada que corresponde a las existencias por producto. */
  fecha_existencia?: string | null;
  productos: ZenitProduct[];
  inferencia: {
    fecha_corte: string;
    tiempo_inferencia_ms: number;
    cumple_umbral_tiempo: boolean;
  } | null;
}

export interface ZenitAgentStatus {
  ollama_disponible: boolean;
  url: string;
  modelos: string[];
  modelo_activo: string | null;
  detalle: string;
}

export interface ZenitAgentTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ZenitAgentToolUse {
  nombre: string;
  fuente: string;
}

export interface ZenitAgentOrderSummary {
  id: number;
  producto: string;
  cuadrante_kraljic: string;
  probabilidad_desabasto: number;
  estado: 'pendiente' | 'aprobada';
  cantidad_sugerida: number | null;
  fecha_corte: string;
}

export interface ZenitAgentChatResponse {
  respuesta: string;
  modelo: string;
  herramientas_usadas: ZenitAgentToolUse[];
  fuentes: string[];
  estado_actualizado: ZenitState | null;
  alertas: ZenitProduct[];
  ordenes_pendientes: ZenitAgentOrderSummary[];
}

const API_ORIGIN = isTauri() ? 'http://127.0.0.1:8000' : 'http://localhost:8000';

export async function getZenitStartupError(): Promise<string | null> {
  if (!isTauri()) return null;
  return invoke<string | null>('zenit_api_startup_error');
}

function apiUrl(path: string): string {
  return `${API_ORIGIN}${path}`;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) return body.detail;
  } catch {
    // The local API may return a plain-text server error.
  }
  return `Error del servicio local (${response.status}).`;
}

async function requestState(path: string, init?: RequestInit): Promise<ZenitState> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as ZenitState;
}

export function getZenitState(): Promise<ZenitState> {
  return requestState('/api/zenit/estado', { cache: 'no-store' });
}

export async function uploadZenitDataset(file: File): Promise<void> {
  const response = await fetch(apiUrl('/api/zenit/cargar'), {
    method: 'POST',
    headers: { 'Content-Type': 'text/csv' },
    body: file,
  });
  if (!response.ok) throw new Error(await readError(response));
}

export async function loadZenitCanonicalDataset(): Promise<void> {
  const response = await fetch(apiUrl('/api/zenit/cargar-local'), {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await readError(response));
}

export function predictZenitStock(fechaCorte: string): Promise<ZenitState> {
  return requestState('/api/zenit/predecir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_corte: fechaCorte }),
  });
}

export async function approveZenitOrder(orderId: number): Promise<void> {
  const response = await fetch(apiUrl(`/api/zenit/ordenes/${orderId}/aprobar`), {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await readError(response));
}

export async function getZenitAgentStatus(model?: string): Promise<ZenitAgentStatus> {
  const query = model ? `?modelo=${encodeURIComponent(model)}` : '';
  const response = await fetch(apiUrl(`/api/zenit/agente/estado${query}`), {
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as ZenitAgentStatus;
}

export async function sendZenitAgentMessage(payload: {
  mensaje: string;
  historial: ZenitAgentTurn[];
  modelo?: string | null;
  fecha_corte?: string;
}): Promise<ZenitAgentChatResponse> {
  const response = await fetch(apiUrl('/api/zenit/agente/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mensaje: payload.mensaje,
      historial: payload.historial,
      modelo: payload.modelo ?? undefined,
      fecha_corte: payload.fecha_corte,
    }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as ZenitAgentChatResponse;
}
