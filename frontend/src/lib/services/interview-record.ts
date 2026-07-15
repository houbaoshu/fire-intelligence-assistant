import { api } from "../api-client";
import type { GenerateResponse, RecordStatus } from "./inspection-record";

export type InterviewRecord = {
  id: string;
  revision: number;
  title?: string | null;
  interviewee_name?: string | null;
  interviewer_names: string[];
  location?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  transcript?: string | null;
  structured_content: {
    sections?: Array<{ question?: string; answer?: string }>;
    [key: string]: unknown;
  };
  status: RecordStatus;
  created_at: string;
  updated_at: string;
};

export const interviewRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/interview-record/generate", form),
  get: (id: string, signal?: AbortSignal) =>
    api.get<InterviewRecord>(`/api/interview-record/${id}`, { signal }),
  update: (id: string, patch: InterviewRecord) =>
    api.put<InterviewRecord>(`/api/interview-record/${id}`, patch),
  download: (id: string) =>
    api.get<Blob>(`/api/interview-record/${id}/download`, { responseType: "blob" }),
};
