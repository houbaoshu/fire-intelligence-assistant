import { api, API_BASE_URL } from "../api-client";

export type GenerateResponse = { task_id: string };

/** Shared shape used by the frontend; backend response schema not yet defined. */
export type InspectionRecord = {
  id: string;
  status?: string;
  basic_info?: Record<string, unknown>;
  findings?: Array<Record<string, unknown>>;
  [k: string]: unknown;
};

export const inspectionRecordService = {
  generate: (form: FormData) =>
    api.post<GenerateResponse>("/api/inspection-record/generate", form),
  get: (id: string) => api.get<InspectionRecord>(`/api/inspection-record/${id}`),
  update: (id: string, patch: Partial<InspectionRecord>) =>
    api.put<InspectionRecord>(`/api/inspection-record/${id}`, patch),
  downloadUrl: (id: string) => `${API_BASE_URL}/api/inspection-record/${id}/download`,
};
