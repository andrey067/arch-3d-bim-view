/**
 * Minimal `fetch` wrapper with correlation id support.
 * No authentication — open access.
 */
import { API_BASE_URL } from '@/app/apiBase';

export type ApiInit = Omit<RequestInit, 'body' | 'signal'> & {
  body?: unknown;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const correlationId = (): string =>
  globalThis.crypto?.randomUUID?.() ?? `cid-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const buildUrl = (path: string): string => {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const base = API_BASE_URL.replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}`;
};

const toBody = (body: unknown, headers: Headers): BodyInit | null => {
  if (body === undefined || body === null) return null;
  if (body instanceof FormData) return body;
  headers.set('Content-Type', 'application/json');
  return JSON.stringify(body);
};

const perform = async (method: string, path: string, init: ApiInit): Promise<Response> => {
  const headers = new Headers(init.headers);
  headers.set('X-Correlation-Id', correlationId());
  const body = toBody(init.body, headers);
  return fetch(buildUrl(path), { ...init, method, headers, body });
};

const parseError = async (response: Response): Promise<ApiError> => {
  let code = 'unknown_error';
  let message = `Request failed with status ${response.status}`;
  let details: unknown;
  try {
    const data = (await response.json()) as { error?: { code?: string; message?: string; details?: unknown } };
    if (data?.error?.code) code = data.error.code;
    if (data?.error?.message) message = data.error.message;
    if (data?.error?.details) details = data.error.details;
  } catch {
    // body was not JSON — keep defaults
  }
  return new ApiError(response.status, code, message, details);
};

const request = async <T>(method: string, path: string, init: ApiInit = {}): Promise<T> => {
  const response = await perform(method, path, init);
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
};

export const apiClient = {
  get: <T>(path: string, init?: ApiInit) => request<T>('GET', path, init),
  post: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>('POST', path, { ...init, body }),
  put: <T>(path: string, body?: unknown, init?: ApiInit) => request<T>('PUT', path, { ...init, body }),
  patch: <T>(path: string, body?: unknown, init?: ApiInit) =>
    request<T>('PATCH', path, { ...init, body }),
  delete: <T>(path: string, init?: ApiInit) => request<T>('DELETE', path, init),
};
