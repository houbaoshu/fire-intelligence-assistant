import { api, API_BASE_URL } from "../api-client";
import type { GenerateResponse } from "./inspection-record";

export type PhotoReport = {
  id: string;
  status?: string;
  address?: string;
  images?: Array<{
    id: string;
    url: string;
    caption?: string;
    timestamp?: number;
    included?: boolean;
  }>;
  [k: string]: unknown;
};

export const photoReportService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/photo-report/generate", form),
  get: (id: string) => api.get<PhotoReport>(`/api/photo-report/${id}`),
  update: (id: string, patch: Partial<PhotoReport>) =>
    api.put<PhotoReport>(`/api/photo-report/${id}`, patch),
  downloadUrl: (id: string) => `${API_BASE_URL}/api/photo-report/${id}/download`,
};
