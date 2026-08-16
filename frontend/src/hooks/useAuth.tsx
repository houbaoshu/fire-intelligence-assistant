/**
 * AuthProvider + useAuth hook.
 *
 * On mount, validates the stored session with GET /api/auth/me; the status
 * starts as "loading" so protected content never flashes before the session
 * is resolved.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  authService,
  clearSession,
  getAccessToken,
  getRefreshToken,
  getStoredUser,
  hasValidRefreshToken,
  persistSession,
  subscribeAuth,
  type AuthStatus,
  type AuthUser,
} from "../lib/auth";

type AuthContextValue = {
  user: AuthUser | null;
  status: AuthStatus;
  /** Login with email/password; throws on failure. */
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (email: string, password: string, fullName?: string) => Promise<AuthUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser());
  const [status, setStatus] = useState<AuthStatus>("loading");
  const initialized = useRef(false);

  useEffect(() => {
    const unsubscribe = subscribeAuth(() => {
      setUser(getStoredUser());
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    let cancelled = false;
    async function init() {
      const stored = getStoredUser();
      if (!hasValidRefreshToken()) {
        if (!cancelled) {
          clearSession();
          setStatus("anonymous");
        }
        return;
      }
      if (!stored) {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      try {
        const me = await authService.me();
        if (!cancelled) {
          persistSession(getAccessTokenOrThrow(), getRefreshTokenOrThrow(), me);
          setUser(me);
          setStatus("authenticated");
        }
      } catch {
        // access token expired -> api-client refreshed already; if that failed
        // the session was cleared by the client. Fall back to the stored user
        // only if a refresh token still exists (session may be resumable).
        if (!cancelled) {
          if (hasValidRefreshToken()) {
            setUser(stored);
            setStatus("authenticated");
          } else {
            clearSession();
            setStatus("anonymous");
          }
        }
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authService.login(email, password);
    persistSession(res.access_token, res.refresh_token, res.user);
    setUser(res.user);
    setStatus("authenticated");
    return res.user;
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const res = await authService.register(email, password, fullName);
    persistSession(res.access_token, res.refresh_token, res.user);
    setUser(res.user);
    setStatus("authenticated");
    return res.user;
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function getAccessTokenOrThrow(): string {
  const t = getAccessToken();
  if (!t) throw new Error("no access token");
  return t;
}

function getRefreshTokenOrThrow(): string {
  const t = getRefreshToken();
  if (!t) throw new Error("no refresh token");
  return t;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
