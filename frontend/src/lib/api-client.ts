/**
 * Centralized API client for the Fire Intelligence Platform backend.
 *
 * Uses VITE_API_BASE_URL. All backend calls MUST go through this module so
 * error shape, auth, and base URL handling stay consistent.
 */

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, "") ?? "";

export type ApiErrorBody = {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export class ApiUnavailableError extends ApiError {
  constructor(message = "Backend base URL is not configured. Set VITE_API_BASE_URL.") {
    super(0, "API_BASE_URL_MISSING", message);
    this.name = "ApiUnavailableError";
  }
}

const AUTH_STORAGE_KEY = "fip.auth.token";
export const AUTH_EXPIRED_EVENT = "fip:auth-expired";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(AUTH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(AUTH_STORAGE_KEY, token);
    else window.localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export type RequestOptions = {
  method?: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  headers?: Record<string, string>;
  /** Bypass auth token even if present. Defaults false. */
  anonymous?: boolean;
  signal?: AbortSignal;
  /** Response type. Defaults to "json". */
  responseType?: "json" | "blob" | "text" | "none";
};

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  if (!API_BASE_URL) throw new ApiUnavailableError();
  const base = API_BASE_URL;
  const p = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${base}${p}`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

export async function apiRequest<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, opts.query);

  const headers: Record<string, string> = { Accept: "application/json", ...(opts.headers ?? {}) };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] ??= "application/json";
    body = JSON.stringify(opts.body);
  }

  if (!opts.anonymous) {
    const tok = getAuthToken();
    if (tok) headers["Authorization"] = `Bearer ${tok}`;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: opts.method ?? (body ? "POST" : "GET"),
      headers,
      body,
      signal: opts.signal,
    });
  } catch (err) {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      err instanceof Error ? err.message : "Network request failed",
    );
  }

  if (!res.ok) {
    let code = `HTTP_${res.status}`;
    let message = res.statusText || "Request failed";
    let details: unknown;
    try {
      const j = (await res.json()) as Partial<ApiErrorBody>;
      if (j && j.error) {
        code = j.error.code ?? code;
        message = j.error.message ?? message;
        details = j.error.details;
      }
    } catch {
      /* ignore parse errors */
    }
    if (res.status === 401 && !opts.anonymous) {
      setAuthToken(null);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
      }
    }
    throw new ApiError(res.status, code, message, details);
  }

  const type = opts.responseType ?? "json";
  if (type === "none" || res.status === 204) return undefined as T;
  if (type === "blob") return (await res.blob()) as T;
  if (type === "text") return (await res.text()) as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const api = {
  get: <T>(path: string, opts?: Omit<RequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...opts, method: "POST", body }),
  put: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...opts, method: "PUT", body }),
  delete: <T>(path: string, opts?: Omit<RequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...opts, method: "DELETE" }),
};

export function isApiConfigured(): boolean {
  return API_BASE_URL.length > 0;
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
