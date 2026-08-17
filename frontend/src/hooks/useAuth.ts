import { createContext, useContext } from "react";
import type { AuthUser } from "@/lib/services/auth";

export type AuthContextValue = {
  /** 当前认证用户；未认证或校验未通过时为 null。 */
  user: AuthUser | null;
  /** 会话存在且 GET /api/auth/me 校验进行中。初始化完成前不得渲染受保护内容。 */
  isInitializing: boolean;
  /** 持有有效会话。网络错误/后端不可用不会清除会话，仅 401（含 refresh 失败）判为未认证。 */
  isAuthenticated: boolean;
  /** 登录/注册成功后写入当前用户，避免再次请求。 */
  setUser: (user: AuthUser) => void;
  /** 退出登录：清除本地会话与缓存并跳转登录页。 */
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
