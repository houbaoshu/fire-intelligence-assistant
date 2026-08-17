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

/*
 * Token 存储说明（specs/authentication.md 要求显式记录）：
 * access_token 与 refresh_token 均存放于 localStorage（key 见下）。
 * localStorage 无法设置 HttpOnly，存在 XSS 窃取风险，缓解措施：
 * - token 只在本模块内读写，绝不进入 URL、日志、分析事件或错误详情；
 * - 页面内容一律经 React 转义渲染，不注入不可信 HTML；
 * - access_token 为短命令牌，泄露窗口由下方的 refresh 续期机制收窄。
 * 后端若日后支持 HttpOnly cookie 会话，应优先迁移至该方案。
 */
const AUTH_STORAGE_KEY = "fip.auth.token";
const REFRESH_STORAGE_KEY = "fip.auth.refresh_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(AUTH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(AUTH_STORAGE_KEY, token);
    else window.localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setRefreshToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(REFRESH_STORAGE_KEY, token);
    else window.localStorage.removeItem(REFRESH_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function setAuthSession(session: { accessToken: string; refreshToken: string | null }) {
  setAuthToken(session.accessToken);
  setRefreshToken(session.refreshToken);
}

export function clearAuthSession() {
  setAuthToken(null);
  setRefreshToken(null);
}

export function hasAuthSession(): boolean {
  return getAuthToken() !== null;
}

/**
 * 会话过期监听：仅在 refresh_token 无效/过期（或缺失）导致会话被销毁时触发一次。
 * 由 AuthProvider 注册，负责清理缓存并跳转登录页；api-client 自身不做路由跳转。
 */
type SessionExpiredListener = () => void;
const sessionExpiredListeners = new Set<SessionExpiredListener>();

export function onSessionExpired(listener: SessionExpiredListener): () => void {
  sessionExpiredListeners.add(listener);
  return () => {
    sessionExpiredListeners.delete(listener);
  };
}

function notifySessionExpired() {
  for (const listener of sessionExpiredListeners) {
    try {
      listener();
    } catch {
      /* 监听器异常不影响会话清理 */
    }
  }
}

type RefreshTokenResponse = { access_token: string; token_type: string };

// 共享的 in-flight refresh promise：并发的多个 401 合并为一次刷新 + 至多一次会话过期流程。
let inFlightRefresh: Promise<boolean> | null = null;

function refreshAccessToken(): Promise<boolean> {
  inFlightRefresh ??= performRefresh().finally(() => {
    inFlightRefresh = null;
  });
  return inFlightRefresh;
}

async function performRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    expireSession();
    return false;
  }
  try {
    const res = await apiRequest<RefreshTokenResponse>("/api/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      anonymous: true,
      skipAuthRefresh: true,
    });
    setAuthToken(res.access_token);
    return true;
  } catch (err) {
    // 仅 refresh_token 无效/过期（401）才销毁会话；网络错误等保留会话，交由调用方展示可读错误。
    if (err instanceof ApiError && err.status === 401) expireSession();
    return false;
  }
}

function expireSession() {
  clearAuthSession();
  notifySessionExpired();
}

export type RequestOptions = {
  method?: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  headers?: Record<string, string>;
  /** Bypass auth token even if present. Defaults false. */
  anonymous?: boolean;
  /** Internal: do not attempt refresh-and-retry on 401 (used for the retry itself). */
  skipAuthRefresh?: boolean;
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

  // access_token 过期：先用 refresh_token 透明续期，再原样重试一次。
  // 匿名请求（login/register/refresh）与已是重试的请求不进入此流程。
  if (res.status === 401 && !opts.anonymous && !opts.skipAuthRefresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiRequest<T>(path, { ...opts, skipAuthRefresh: true });
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
