import { useEffect, useMemo, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { toast } from "sonner";
import { ApiError, hasAuthSession, onSessionExpired } from "@/lib/api-client";
import { authMeQueryOptions, authService, type AuthUser } from "@/lib/services/auth";
import { AuthContext, type AuthContextValue } from "@/hooks/useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const hasSession = hasAuthSession();
  const me = useQuery({ ...authMeQueryOptions(), enabled: hasSession });

  // 401（含 api-client 内部 refresh 重试后仍失败）说明会话已失效；
  // 网络错误 / 后端不可用不清除会话，交由页面级错误态展示。
  const unauthorized = me.error instanceof ApiError && me.error.status === 401;
  const isAuthenticated = hasSession && !unauthorized;
  const isInitializing = hasSession && me.isPending;

  // 会话过期只可能由 api-client 的共享 refresh 流程触发一次，这里统一处理跳转。
  useEffect(
    () =>
      onSessionExpired(() => {
        queryClient.removeQueries({ queryKey: ["auth", "me"] });
        const { pathname, href } = router.state.location;
        // 防止重定向循环：已在公开页时不再跳转。
        if (pathname === "/login" || pathname === "/register") return;
        toast.error("登录已过期，请重新登录");
        void router.navigate({ to: "/login", search: { redirect: href } });
      }),
    [router, queryClient],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user: me.data ?? null,
      isInitializing,
      isAuthenticated,
      setUser: (user: AuthUser) => queryClient.setQueryData(["auth", "me"], user),
      logout: () => {
        authService.logout();
        queryClient.removeQueries({ queryKey: ["auth", "me"] });
        void router.navigate({ to: "/login" });
      },
    }),
    [me.data, isInitializing, isAuthenticated, queryClient, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
