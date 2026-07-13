import { api, API_BASE_URL } from "../api-client";
import type { GenerateResponse } from "./inspection-record";

export type InterviewRecord = {
  id: string;
  status?: string;
  transcript?: string;
  structured?: Record<string, unknown>;
  [k: string]: unknown;
};

export const interviewRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/interview-record/generate", form),
  get: (id: string) => api.get<InterviewRecord>(`/api/interview-record/${id}`),
  update: (id: string, patch: Partial<InterviewRecord>) =>
    api.put<InterviewRecord>(`/api/interview-record/${id}`, patch),
  downloadUrl: (id: string) => `${API_BASE_URL}/api/interview-record/${id}/download`,
};
