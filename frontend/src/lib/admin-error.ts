import { ApiError } from "./api-client";

/**
 * /admin 路由区统一的可读错误文案:
 * 403 补充权限说明;409(归属冲突 / 自锁保护)等原样展示后端 message。
 */
export function readableAdminError(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return `没有权限执行此操作(${e.message})`;
    return e.message;
  }
  return e instanceof Error ? e.message : fallback;
}
