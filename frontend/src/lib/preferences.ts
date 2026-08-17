/**
 * 本地界面偏好(specs/settings.md v1 范围):主题 / 显示密度 / 减弱动效 / 列表默认 page-size。
 * 一律存浏览器 localStorage,不做服务端同步;非法值按字段安全回退到默认值。
 */

export type ThemePref = "light" | "dark" | "system";
export type DensityPref = "comfortable" | "compact";

export type Preferences = {
  theme: ThemePref;
  density: DensityPref;
  reducedMotion: boolean;
  pageSize: number;
};

export const DEFAULT_PREFERENCES: Preferences = {
  theme: "system",
  density: "comfortable",
  reducedMotion: false,
  pageSize: 20,
};

export const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

const PREF_KEY = "fip.prefs.v1";

const THEMES: ThemePref[] = ["light", "dark", "system"];
const DENSITIES: DensityPref[] = ["comfortable", "compact"];

export function loadPreferences(): Preferences {
  if (typeof window === "undefined") return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(PREF_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const prefs = { ...DEFAULT_PREFERENCES };
    if (THEMES.includes(parsed.theme as ThemePref)) prefs.theme = parsed.theme as ThemePref;
    if (DENSITIES.includes(parsed.density as DensityPref))
      prefs.density = parsed.density as DensityPref;
    // 兼容 M1 的 compactUi 偏好:迁移为 density。
    if (parsed.compactUi === true && !DENSITIES.includes(parsed.density as DensityPref))
      prefs.density = "compact";
    if (typeof parsed.reducedMotion === "boolean") prefs.reducedMotion = parsed.reducedMotion;
    if (
      typeof parsed.pageSize === "number" &&
      (PAGE_SIZE_OPTIONS as readonly number[]).includes(parsed.pageSize)
    )
      prefs.pageSize = parsed.pageSize;
    return prefs;
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function savePreferences(prefs: Preferences): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
  } catch {
    /* 读写失败不得阻止应用加载 */
  }
}

/** 将偏好应用到文档根元素:主题(dark class)、密度(data 属性)、减弱动效(class)。 */
export function applyPreferences(prefs: Preferences): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const dark =
    prefs.theme === "dark" ||
    (prefs.theme === "system" &&
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  root.classList.toggle("dark", dark);
  root.dataset.density = prefs.density;
  root.classList.toggle("reduce-motion", prefs.reducedMotion);
}
