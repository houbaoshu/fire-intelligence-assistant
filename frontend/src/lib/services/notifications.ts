import { api } from "../api-client";

/**
 * 通知(API.md §10 通知契约,后端按同一契约实现)。
 * 文案 title/body 由后端生成,前端只负责展示,禁止拼接假内容。
 */
export type AppNotification = {
  id: string;
  /** 机器类型值,如 task_completed / task_failed;未知值按通用样式展示。 */
  type: string;
  title: string;
  body: string | null;
  /** 关联实体类型(如 inspection_record / task);用于安全导航映射。 */
  entity_type: string | null;
  entity_id: string | null;
  /** 已读时间;null 表示未读。 */
  read_at: string | null;
  created_at: string;
};

/** GET /api/notifications 列表响应信封。 */
export type NotificationListResponse = {
  items: AppNotification[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
};

export type NotificationListParams = {
  unread_only?: boolean;
  page?: number;
  page_size?: number;
};

export const notificationService = {
  list: (params: NotificationListParams = {}, signal?: AbortSignal) =>
    api.get<NotificationListResponse>("/api/notifications", {
      query: {
        unread_only: params.unread_only,
        page: params.page,
        page_size: params.page_size,
      },
      signal,
    }),
  markRead: (id: string) =>
    api.post<{ id: string; read_at: string }>(`/api/notifications/${encodeURIComponent(id)}/read`),
  markAllRead: () => api.post<{ updated: number }>("/api/notifications/read-all"),
};
