import { api } from "../api-client";

export type TaskStatus = "pending" | "queued" | "processing" | "completed" | "failed" | "cancelled";

export type TaskOut = {
  task_id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  current_stage: string | null;
  result_data: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type TaskListResponse = {
  items: TaskOut[];
  total: number;
};

export const TASK_TYPE_LABELS: Record<string, string> = {
  inspection_record_generation: "检查记录生成",
  photo_report_generation: "拍照报告生成",
  interview_record_generation: "询问记录生成",
  speech_transcription: "语音转写",
  video_analysis: "视频分析",
  document_generation: "文书生成",
  knowledge_indexing: "知识库索引",
  knowledge_reindexing: "知识库重建",
};

export const TASK_STATUS_LABELS: Record<string, string> = {
  pending: "待处理",
  queued: "排队中",
  processing: "处理中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const TERMINAL_TASK_STATES: TaskStatus[] = ["completed", "failed", "cancelled"];

export function isTerminalTaskState(status: TaskStatus): boolean {
  return TERMINAL_TASK_STATES.includes(status);
}

const enc = encodeURIComponent;

export const taskService = {
  get: (taskId: string, signal?: AbortSignal) =>
    api.get<TaskOut>("/api/tasks/" + enc(taskId), { signal }),
  list: (
    params: { limit?: number; status?: string; task_type?: string } = {},
    signal?: AbortSignal,
  ) => api.get<TaskListResponse>("/api/tasks", { query: params, signal }),
  retry: (taskId: string) =>
    api.post<{ task_id: string; status: string }>("/api/tasks/" + enc(taskId) + "/retry"),
  cancel: (taskId: string) =>
    api.post<{ task_id: string; status: string }>("/api/tasks/" + enc(taskId) + "/cancel"),
};
