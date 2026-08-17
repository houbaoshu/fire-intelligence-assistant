import { api, clearAuthSession, setAuthSession } from "../api-client";

/**
 * 认证服务：严格对齐 docs/API.md §2。
 * 所有请求一律走集中式 api-client；token 的持久化由 api-client 的会话工具完成，
 * 本模块不直接触碰 localStorage，也不把 token 写入日志或错误详情。
 */

/** 角色枚举见 DATABASE.md users 表。 */
export type UserRole = "admin" | "supervisor" | "inspector" | "viewer";

export const USER_ROLES: UserRole[] = ["admin", "supervisor", "inspector", "viewer"];

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  /** GET /api/auth/me 追加的权限码列表(API.md §11);旧后端未返回时为 undefined,调用方须可选链处理。 */
  permissions?: string[];
};

/** POST /api/auth/login 与 /api/auth/register 的响应（两者结构相同）。 */
export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
};

/** POST /api/auth/refresh 的响应。 */
export type RefreshResponse = {
  access_token: string;
  token_type: string;
};

/** GET /api/auth/me 的查询选项，路由守卫（ensureQueryData）与 AuthProvider（useQuery）共用。 */
export const authMeQueryOptions = () => ({
  queryKey: ["auth", "me"] as const,
  queryFn: ({ signal }: { signal: AbortSignal }) => authService.me(signal),
  staleTime: 60_000,
  retry: false,
});

function persistSession(res: AuthResponse): AuthUser {
  setAuthSession({ accessToken: res.access_token, refreshToken: res.refresh_token });
  return res.user;
}

export const authService = {
  /** 邮箱密码登录；成功即持久化会话并返回当前用户。 */
  login: async (email: string, password: string): Promise<AuthUser> => {
    const res = await api.post<AuthResponse>(
      "/api/auth/login",
      { email, password },
      { anonymous: true },
    );
    return persistSession(res);
  },

  /** 注册并直接建立会话（注册是否开放由后端决定，失败按错误信封展示）。 */
  register: async (email: string, password: string, fullName: string): Promise<AuthUser> => {
    const res = await api.post<AuthResponse>(
      "/api/auth/register",
      { email, password, full_name: fullName },
      { anonymous: true },
    );
    return persistSession(res);
  },

  /** 当前 token 对应的用户。 */
  me: (signal?: AbortSignal) => api.get<AuthUser>("/api/auth/me", { signal }),

  /** 用 refresh_token 换取新的 access_token（常规续期由 api-client 自动完成，此处供显式调用）。 */
  refresh: (refreshToken: string) =>
    api.post<RefreshResponse>(
      "/api/auth/refresh",
      { refresh_token: refreshToken },
      { anonymous: true },
    ),

  /** 退出登录：仅清除本地会话，此后请求不再携带旧凭证。 */
  logout: () => clearAuthSession(),
};
