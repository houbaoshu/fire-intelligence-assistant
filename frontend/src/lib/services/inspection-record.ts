import { api } from "../api-client";
import type { GenerateResponse, ListParams, Paginated, RecordStatus } from "./common";

/** 列表元素(API.md §4.1)。 */
export type InspectionRecordListItem = {
  id: string;
  record_number: string | null;
  title: string | null;
  inspection_unit: string | null;
  inspection_date: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
};

/** 发现项类型枚举(定义权:docs/DATABASE.md inspection_record_items)。 */
export type InspectionItemType =
  | "compliant"
  | "violation"
  | "hazard"
  | "observation"
  | "recommendation";

export const INSPECTION_ITEM_TYPES: InspectionItemType[] = [
  "compliant",
  "violation",
  "hazard",
  "observation",
  "recommendation",
];

/** 严重程度枚举(定义权:docs/DATABASE.md inspection_record_items)。 */
export type InspectionSeverity = "low" | "medium" | "high" | "critical";

export const INSPECTION_SEVERITIES: InspectionSeverity[] = ["low", "medium", "high", "critical"];

/** 检查发现项(详情内嵌)。 */
export type InspectionRecordItem = {
  id: string;
  item_type: InspectionItemType;
  location: string | null;
  description: string;
  legal_basis: string | null;
  correction_requirement: string | null;
  severity: InspectionSeverity | null;
  sort_order: number;
};

/** 详情响应(API.md §4.1)。 */
export type InspectionRecordDetail = {
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
  status: RecordStatus;
  items: InspectionRecordItem[];
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

/** PUT 更新的检查项:新增不传 id;省略已有 id 即删除(整体替换语义,API.md §4.1)。 */
export type InspectionRecordItemUpdate = Omit<InspectionRecordItem, "id"> & { id?: string };

/** PUT 可编辑字段,均为可选,未提交字段保持不变。 */
export type InspectionRecordUpdate = {
  title?: string | null;
  inspection_unit?: string | null;
  inspection_address?: string | null;
  inspection_date?: string | null;
  inspector_names?: string[] | null;
  contact_person?: string | null;
  contact_phone?: string | null;
  summary?: string | null;
  conclusion?: string | null;
  status?: RecordStatus;
  items?: InspectionRecordItemUpdate[];
};

const base = "/api/inspection-record";

export const inspectionRecordService = {
  generate: (form: FormData) => api.post<GenerateResponse>(`${base}/generate`, form),
  list: (params: ListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<InspectionRecordListItem>>(base, {
      query: { page: params.page, page_size: params.page_size, status: params.status },
      signal,
    }),
  get: (id: string, signal?: AbortSignal) =>
    api.get<InspectionRecordDetail>(`${base}/${encodeURIComponent(id)}`, { signal }),
  update: (id: string, patch: InspectionRecordUpdate) =>
    api.put<InspectionRecordDetail>(`${base}/${encodeURIComponent(id)}`, patch),
  /** 下载 Word 文书(文件流);文档未生成返回 409,由 api-client 转为 ApiError。 */
  download: (id: string) =>
    api.get<Blob>(`${base}/${encodeURIComponent(id)}/download`, { responseType: "blob" }),
};
