/**
 * 业务记录共享契约类型(定义权:docs/API.md §4、docs/DATABASE.md)。
 * 各业务 service 复用本模块,避免重复定义。
 */

/** 异步生成任务提交响应(API.md §4)。 */
export type GenerateResponse = { task_id: string };

/** 分页列表信封(API.md §4.1)。 */
export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

/** 业务记录状态枚举(定义权:docs/DATABASE.md 各记录表)。 */
export type RecordStatus =
  | "draft"
  | "processing"
  | "generated"
  | "reviewed"
  | "finalized"
  | "archived"
  | "failed";

export const RECORD_STATUSES: RecordStatus[] = [
  "draft",
  "processing",
  "generated",
  "reviewed",
  "finalized",
  "archived",
  "failed",
];

/** 列表查询参数(page 默认 1,page_size 默认 20、最大 100)。 */
export type ListParams = {
  page?: number;
  page_size?: number;
  status?: RecordStatus;
};
