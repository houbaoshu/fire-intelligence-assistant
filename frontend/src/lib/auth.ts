/**
 * Authentication state store and API calls.
 */
import { api } from "./api-client";
import {
  clearTokens,
  getAccessToken as readAccessToken,
  getRefreshToken as readRefreshToken,
  getStoredUserJson,
  setTokens,
} from "./auth-tokens";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
};

export type AuthStatus = "loading" | "authenticated" | "anonymous";

type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribeAuth(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit() {
  for (const l of listeners) l();
}

/** Current access token (used by protected API calls). */
export function getAccessToken(): string | null {
  return readAccessToken();
}

/** Current refresh token. */
export function getRefreshToken(): string | null {
  return readRefreshToken();
}

export function getStoredUser(): AuthUser | null {
  const raw = getStoredUserJson();
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function persistSession(accessToken: string, refreshToken: string, user: AuthUser) {
  setTokens(accessToken, refreshToken, JSON.stringify(user));
  emit();
}

export function clearSession() {
  clearTokens();
  emit();
}

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
};

export const authService = {
  login: (email: string, password: string) =>
    api.post<LoginResponse>("/api/auth/login", { email, password }, { anonymous: true }),
  register: (email: string, password: string, fullName?: string) =>
    api.post<LoginResponse>(
      "/api/auth/register",
      { email, password, full_name: fullName ?? null },
      { anonymous: true },
    ),
  me: () => api.get<AuthUser>("/api/auth/me"),
  refresh: (refreshToken: string) =>
    api.post<{ access_token: string }>(
      "/api/auth/refresh",
      { refresh_token: refreshToken },
      { anonymous: true },
    ),
};

export function hasValidRefreshToken(): boolean {
  return Boolean(readRefreshToken());
}
