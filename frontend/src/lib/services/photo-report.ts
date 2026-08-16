import { api, API_BASE_URL } from "../api-client";

export type GenerateResponse = { task_id: string };

export type PhotoReportImage = {
  id: string;
  uploaded_file_id: string;
  frame_timestamp: number | null;
  caption: string | null;
  detected_address: string | null;
  detected_violation: string | null;
  is_selected: boolean;
  sort_order: number;
  created_at: string;
};

export type PhotoReport = {
  id: string;
  title: string | null;
  inspection_unit: string | null;
  inspection_address: string | null;
  violation_summary: string | null;
  status: string;
  images: PhotoReportImage[];
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PhotoReportListItem = {
  id: string;
  title: string | null;
  inspection_unit: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type PhotoReportListResponse = {
  items: PhotoReportListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type PhotoReportUpdate = Partial<
  Pick<
    PhotoReport,
    "title" | "inspection_unit" | "inspection_address" | "violation_summary" | "status"
  >
> & {
  images?: Array<{
    id: string;
    caption?: string | null;
    is_selected?: boolean;
    sort_order?: number;
  }>;
};

export const photoReportService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/photo-report/generate", form),
  list: (
    params: { page?: number; page_size?: number; status?: string } = {},
    signal?: AbortSignal,
  ) => api.get<PhotoReportListResponse>("/api/photo-report", { query: params, signal }),
  get: (id: string, signal?: AbortSignal) =>
    api.get<PhotoReport>("/api/photo-report/" + encodeURIComponent(id), { signal }),
  update: (id: string, patch: PhotoReportUpdate) =>
    api.put<PhotoReport>("/api/photo-report/" + encodeURIComponent(id), patch),
  downloadUrl: (id: string) =>
    API_BASE_URL + "/api/photo-report/" + encodeURIComponent(id) + "/download",
  imageUrl: (uploadedFileId: string) =>
    API_BASE_URL + "/api/files/" + encodeURIComponent(uploadedFileId) + "/content",
};
