import { api } from "../api-client";
import type { GenerateResponse, RecordStatus } from "./inspection-record";

export type PhotoReportImage = {
  id: string;
  caption?: string | null;
  detected_address?: string | null;
  detected_violation?: string | null;
  is_selected: boolean;
  needs_review: boolean;
  sort_order: number;
  frame_timestamp?: number | null;
  preview_url: string;
};

export type PhotoReport = {
  id: string;
  revision: number;
  title?: string | null;
  inspection_unit?: string | null;
  inspection_address?: string | null;
  violation_summary?: string | null;
  status: RecordStatus;
  images: PhotoReportImage[];
  created_at: string;
  updated_at: string;
};

export const photoReportService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/photo-report/generate", form),
  get: (id: string, signal?: AbortSignal) =>
    api.get<PhotoReport>(`/api/photo-report/${id}`, { signal }),
  update: (id: string, patch: PhotoReport) =>
    api.put<PhotoReport>(`/api/photo-report/${id}`, patch),
  preview: (reportId: string, imageId: string, signal?: AbortSignal) =>
    api.get<Blob>(`/api/photo-report/${reportId}/images/${imageId}`, {
      responseType: "blob",
      signal,
    }),
  download: (id: string) =>
    api.get<Blob>(`/api/photo-report/${id}/download`, { responseType: "blob" }),
};
