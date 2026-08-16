import { api, API_BASE_URL } from "../api-client";

export type GenerateResponse = { task_id: string };

export type InspectionItem = {
  id: string;
  item_type: "compliant" | "violation" | "hazard" | "observation" | "recommendation";
  location: string | null;
  description: string;
  legal_basis: string | null;
  correction_requirement: string | null;
  severity: "low" | "medium" | "high" | "critical" | null;
  sort_order: number;
};

export type InspectionRecord = {
  id: string;
  record_number: string | null;
  title: string | null;
  inspection_unit: string | null;
  inspection_address: string | null;
  inspection_date: string | null;
  inspector_names: string[] | null;
  contact_person: string | null;
  contact_phone: string | null;
  summary: string | null;
  conclusion: string | null;
  status: string;
  items: InspectionItem[];
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

export type InspectionRecordListItem = {
  id: string;
  record_number: string | null;
  title: string | null;
  inspection_unit: string | null;
  inspection_date: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type InspectionRecordListResponse = {
  items: InspectionRecordListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type InspectionUpdate = Partial<
  Pick<
    InspectionRecord,
    | "title"
    | "inspection_unit"
    | "inspection_address"
    | "inspection_date"
    | "inspector_names"
    | "contact_person"
    | "contact_phone"
    | "summary"
    | "conclusion"
    | "status"
  >
> & {
  items?: Array<{
    id?: string;
    item_type: InspectionItem["item_type"];
    location?: string | null;
    description: string;
    legal_basis?: string | null;
    correction_requirement?: string | null;
    severity?: InspectionItem["severity"];
    sort_order?: number;
  }>;
};

export const inspectionRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>("/api/inspection-record/generate", form),
  list: (
    params: { page?: number; page_size?: number; status?: string } = {},
    signal?: AbortSignal,
  ) => api.get<InspectionRecordListResponse>("/api/inspection-record", { query: params, signal }),
  get: (id: string, signal?: AbortSignal) =>
    api.get<InspectionRecord>("/api/inspection-record/" + encodeURIComponent(id), { signal }),
  update: (id: string, patch: InspectionUpdate) =>
    api.put<InspectionRecord>("/api/inspection-record/" + encodeURIComponent(id), patch),
  downloadUrl: (id: string) =>
    API_BASE_URL + "/api/inspection-record/" + encodeURIComponent(id) + "/download",
};
