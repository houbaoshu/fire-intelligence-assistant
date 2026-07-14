import { api } from "../api-client";

export type GenerateResponse = { task_id: string; entity_id?: string | null };
export type RecordStatus =
  "draft" | "processing" | "generated" | "reviewed" | "finalized" | "archived" | "failed";

export type InspectionFinding = {
  id?: string | null;
  item_type: "compliant" | "violation" | "hazard" | "observation" | "recommendation";
  location?: string | null;
  description: string;
  legal_basis?: string | null;
  correction_requirement?: string | null;
  severity?: "low" | "medium" | "high" | "critical" | null;
  sort_order: number;
};

export type InspectionRecord = {
  id: string;
  revision: number;
  record_number?: string | null;
  title?: string | null;
  inspection_unit?: string | null;
  inspection_address?: string | null;
  inspection_date?: string | null;
  inspector_names: string[];
  contact_person?: string | null;
  contact_phone?: string | null;
  source_notes?: string | null;
  summary?: string | null;
  conclusion?: string | null;
  status: RecordStatus;
  findings: InspectionFinding[];
  created_at: string;
  updated_at: string;
};

export const inspectionRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/inspection-record/generate", form),
  get: (id: string, signal?: AbortSignal) =>
    api.get<InspectionRecord>(`/api/inspection-record/${id}`, { signal }),
  update: (id: string, patch: InspectionRecord) =>
    api.put<InspectionRecord>(`/api/inspection-record/${id}`, patch),
  download: (id: string) =>
    api.get<Blob>(`/api/inspection-record/${id}/download`, { responseType: "blob" }),
};
