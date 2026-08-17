import { ApiError } from "./api-client";

/**
 * 认证相关错误 → 可读文案。
 * 401 一律展示通用文案，不区分「邮箱不存在」与「密码错误」，避免账号枚举；
 * 其余错误按契约（API.md §1 错误信封）展示后端返回的可读 message。
 * 注意：不得在此输出 token 或请求体内容。
 */
export function authErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return "无法连接后端服务，请稍后重试";
    if (err.status === 401) return "邮箱或密码不正确";
    if (err.status === 429) return "请求过于频繁，请稍后再试";
    return err.message || "操作失败，请稍后重试";
  }
  return "操作失败，请稍后重试";
}

/**
 * 登录成功后恢复原目标。仅允许站内路径（防止开放重定向），
 * 且排除认证页自身（防止重定向循环）。
 */
export function safeRedirectTarget(target: string | undefined): string {
  if (!target) return "/";
  if (!target.startsWith("/") || target.startsWith("//")) return "/";
  if (target === "/login" || target.startsWith("/login?")) return "/";
  if (target === "/register" || target.startsWith("/register?")) return "/";
  return target;
}
