import { api } from "../api-client";

export type TaskStatus = "pending" | "queued" | "processing" | "completed" | "failed" | "cancelled";

export type TaskState = {
  id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  current_stage?: string | null;
  message?: string | null;
  result?: { entity_type?: string; entity_id?: string; [key: string]: unknown } | null;
  error_code?: string | null;
  error_message?: string | null;
  attempt: number;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
};

export type TaskList = { items: TaskState[]; total: number };

export const taskService = {
  get: (taskId: string, signal?: AbortSignal) =>
    api.get<TaskState>(`/api/tasks/${encodeURIComponent(taskId)}`, { signal }),
  list: (signal?: AbortSignal) => api.get<TaskList>("/api/tasks", { query: { limit: 20 }, signal }),
  retry: (taskId: string) => api.post<TaskState>(`/api/tasks/${encodeURIComponent(taskId)}/retry`),
  cancel: (taskId: string) =>
    api.post<TaskState>(`/api/tasks/${encodeURIComponent(taskId)}/cancel`),
};

export const TERMINAL_TASK_STATES: TaskStatus[] = ["completed", "failed", "cancelled"];

export function isTerminalTaskState(status: TaskStatus): boolean {
  return TERMINAL_TASK_STATES.includes(status);
}
