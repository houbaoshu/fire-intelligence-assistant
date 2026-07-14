import { api } from "../api-client";

export type UserRole = "admin" | "supervisor" | "inspector" | "viewer";

export type AuthUser = {
  id: string;
  email: string;
  username: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
};

export type AuthConfig = {
  registration_enabled: boolean;
};

export const authService = {
  config: (signal?: AbortSignal) =>
    api.get<AuthConfig>("/api/auth/config", { anonymous: true, signal }),
  login: (email: string, password: string) =>
    api.post<AuthTokens>("/api/auth/login", { email, password }, { anonymous: true }),
  register: (email: string, password: string, username?: string) =>
    api.post<AuthUser>(
      "/api/auth/register",
      { email, password, username: username?.trim() || undefined },
      { anonymous: true },
    ),
  me: (signal?: AbortSignal) => api.get<AuthUser>("/api/auth/me", { signal }),
};
