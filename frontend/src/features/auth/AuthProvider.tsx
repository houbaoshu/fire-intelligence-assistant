import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { AUTH_EXPIRED_EVENT, getAuthToken, setAuthToken } from "@/lib/api-client";
import { authService } from "@/lib/services/auth";
import { AuthContext, type AuthContextValue, type AuthState } from "@/features/auth/auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });

  const clearSession = useCallback(() => {
    setAuthToken(null);
    setState({ status: "unauthenticated", user: null });
    queryClient.clear();
  }, [queryClient]);

  const loadUser = useCallback(async (signal?: AbortSignal) => {
    const user = await authService.me(signal);
    setState({ status: "authenticated", user });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    if (!getAuthToken()) {
      setState({ status: "unauthenticated", user: null });
      return () => controller.abort();
    }
    void loadUser(controller.signal).catch(() => {
      if (!controller.signal.aborted) clearSession();
    });
    return () => controller.abort();
  }, [clearSession, loadUser]);

  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, clearSession);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, clearSession);
  }, [clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authService.login(email, password);
      setAuthToken(tokens.access_token);
      try {
        await loadUser();
      } catch (error) {
        clearSession();
        throw error;
      }
    },
    [clearSession, loadUser],
  );

  const register = useCallback(
    async (email: string, password: string, username?: string) => {
      await authService.register(email, password, username);
      await login(email, password);
    },
    [login],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, register, logout: clearSession }),
    [clearSession, login, register, state],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
