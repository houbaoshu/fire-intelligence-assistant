import { api } from "../api-client";

export type TaskStatus =
  | "pending"
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled";

export type TaskState = {
  status: TaskStatus;
  progress?: number;
  message?: string;
};

export const taskService = {
  get: (taskId: string, signal?: AbortSignal) =>
    api.get<TaskState>(`/api/tasks/${encodeURIComponent(taskId)}`, { signal }),
};

export const TERMINAL_TASK_STATES: TaskStatus[] = ["completed", "failed", "cancelled"];

export function isTerminalTaskState(status: TaskStatus): boolean {
  return TERMINAL_TASK_STATES.includes(status);
}
