/**
 * Token storage primitives. Kept dependency-free so both the API client and
 * the auth store can import it without circular imports.
 */
const ACCESS_KEY = "fip.auth.access_token";
const REFRESH_KEY = "fip.auth.refresh_token";
const USER_KEY = "fip.auth.user";

function safeGet(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* ignore storage errors */
  }
}

export function getAccessToken(): string | null {
  return safeGet(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return safeGet(REFRESH_KEY);
}

export function getStoredUserJson(): string | null {
  return safeGet(USER_KEY);
}

export function setTokens(access: string | null, refresh: string | null, userJson: string | null) {
  safeSet(ACCESS_KEY, access);
  safeSet(REFRESH_KEY, refresh);
  safeSet(USER_KEY, userJson);
}

export function clearTokens() {
  safeSet(ACCESS_KEY, null);
  safeSet(REFRESH_KEY, null);
  safeSet(USER_KEY, null);
}
