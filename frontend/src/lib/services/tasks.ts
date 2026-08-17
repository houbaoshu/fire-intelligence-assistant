import { api } from "../api-client";

/** 任务状态枚举(定义权:docs/DATABASE.md ai_tasks 表)。 */
export type TaskStatus = "pending" | "queued" | "processing" | "completed" | "failed" | "cancelled";

/** 任务类型枚举(API.md §8)。 */
export type TaskType =
  | "inspection_record_generation"
  | "photo_report_generation"
  | "interview_record_generation"
  | "speech_transcription"
  | "video_analysis"
  | "document_generation"
  | "knowledge_indexing"
  | "knowledge_reindexing";

/** completed 时 result_data 携带安全结果引用,生成类任务为 { record_id }。 */
export type TaskResultData = { record_id?: string };

/** 任务详情 / 列表元素(API.md §8)。 */
export type Task = {
  task_id: string;
  task_type: TaskType | string;
  status: TaskStatus;
  progress: number | null;
  current_stage: string | null;
  result_data: TaskResultData | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

/** GET /api/tasks 列表响应信封。 */
export type TaskListResponse = {
  items: Task[];
  total: number;
};

export const taskService = {
  get: (taskId: string, signal?: AbortSignal) =>
    api.get<Task>(`/api/tasks/${encodeURIComponent(taskId)}`, { signal }),
  list: (params: { limit?: number; status?: TaskStatus } = {}, signal?: AbortSignal) =>
    api.get<TaskListResponse>("/api/tasks", {
      query: { limit: params.limit, status: params.status },
      signal,
    }),
  /** 仅 failed / cancelled 可重试,其他状态后端返回 409。 */
  retry: (taskId: string) =>
    api.post<{ task_id: string }>(`/api/tasks/${encodeURIComponent(taskId)}/retry`),
  /** 仅 pending / queued / processing 可取消,其他状态后端返回 409。 */
  cancel: (taskId: string) =>
    api.post<{ task_id: string; status: TaskStatus }>(
      `/api/tasks/${encodeURIComponent(taskId)}/cancel`,
    ),
};

export const TERMINAL_TASK_STATES: TaskStatus[] = ["completed", "failed", "cancelled"];

export function isTerminalTaskState(status: TaskStatus): boolean {
  return TERMINAL_TASK_STATES.includes(status);
}
