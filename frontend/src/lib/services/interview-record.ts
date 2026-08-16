import { api, API_BASE_URL } from "../api-client";

export type GenerateResponse = { task_id: string };

export type InterviewRecord = {
  id: string;
  title: string | null;
  interviewee_name: string | null;
  interviewer_names: string[] | null;
  location: string | null;
  started_at: string | null;
  ended_at: string | null;
  transcript: string | null;
  structured_content: {
    questions_and_answers?: Array<{ question: string; answer: string }>;
    [k: string]: unknown;
  } | null;
  status: string;
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

export type InterviewRecordListItem = {
  id: string;
  title: string | null;
  interviewee_name: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type InterviewRecordListResponse = {
  items: InterviewRecordListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type InterviewUpdate = Partial<
  Pick<
    InterviewRecord,
    | "title"
    | "interviewee_name"
    | "interviewer_names"
    | "location"
    | "started_at"
    | "ended_at"
    | "transcript"
    | "structured_content"
    | "status"
  >
>;

export const interviewRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/interview-record/generate", form),
  list: (
    params: { page?: number; page_size?: number; status?: string } = {},
    signal?: AbortSignal,
  ) => api.get<InterviewRecordListResponse>("/api/interview-record", { query: params, signal }),
  get: (id: string, signal?: AbortSignal) =>
    api.get<InterviewRecord>("/api/interview-record/" + encodeURIComponent(id), { signal }),
  update: (id: string, patch: InterviewUpdate) =>
    api.put<InterviewRecord>("/api/interview-record/" + encodeURIComponent(id), patch),
  downloadUrl: (id: string) =>
    API_BASE_URL + "/api/interview-record/" + encodeURIComponent(id) + "/download",
};
