import { api } from "../api-client";
import type { GenerateResponse, ListParams, Paginated, RecordStatus } from "./common";

/** 列表元素(API.md §4.3)。 */
export type InterviewRecordListItem = {
  id: string;
  title: string | null;
  interviewee_name: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
};

/** 结构化问答对(structured_content.questions_and_answers 元素)。 */
export type InterviewQA = {
  question: string;
  answer: string;
};

/**
 * structured_content 为 JSONB,核心为 questions_and_answers;
 * 其余键随后端演进保留(API.md §4.3)。
 */
export type InterviewStructuredContent = {
  questions_and_answers?: InterviewQA[];
} & Record<string, unknown>;

/** 详情响应(API.md §4.3)。 */
export type InterviewRecordDetail = {
  id: string;
  title: string | null;
  interviewee_name: string | null;
  interviewer_names: string[] | null;
  location: string | null;
  started_at: string | null;
  ended_at: string | null;
  transcript: string | null;
  structured_content: InterviewStructuredContent | null;
  status: RecordStatus;
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

/** PUT 可编辑字段,均为可选,未提交字段保持不变。 */
export type InterviewRecordUpdate = {
  title?: string | null;
  interviewee_name?: string | null;
  interviewer_names?: string[] | null;
  location?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  transcript?: string | null;
  structured_content?: InterviewStructuredContent | null;
  status?: RecordStatus;
};

const base = "/api/interview-record";

export const interviewRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>(`${base}/generate`, form),
  list: (params: ListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<InterviewRecordListItem>>(base, {
      query: { page: params.page, page_size: params.page_size, status: params.status },
      signal,
    }),
  get: (id: string, signal?: AbortSignal) =>
    api.get<InterviewRecordDetail>(`${base}/${encodeURIComponent(id)}`, { signal }),
  update: (id: string, patch: InterviewRecordUpdate) =>
    api.put<InterviewRecordDetail>(`${base}/${encodeURIComponent(id)}`, patch),
  /** 下载 Word 文书(文件流);文档未生成返回 409,由 api-client 转为 ApiError。 */
  download: (id: string) =>
    api.get<Blob>(`${base}/${encodeURIComponent(id)}/download`, { responseType: "blob" }),
};
