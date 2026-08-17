import { api } from "../api-client";
import type { GenerateResponse, ListParams, Paginated, RecordStatus } from "./common";

/** 列表元素(API.md §4.2)。 */
export type PhotoReportListItem = {
  id: string;
  title: string | null;
  inspection_unit: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
};

/** 报告图片(详情内嵌)。 */
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

/** 详情响应(API.md §4.2)。 */
export type PhotoReportDetail = {
  id: string;
  title: string | null;
  inspection_unit: string | null;
  inspection_address: string | null;
  violation_summary: string | null;
  status: RecordStatus;
  images: PhotoReportImage[];
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

/** PUT 图片更新:按 id 逐项匹配,仅 caption / is_selected / sort_order 可编辑,不涉及增删。 */
export type PhotoReportImageUpdate = {
  id: string;
  caption?: string | null;
  is_selected?: boolean;
  sort_order?: number;
};

/** PUT 可编辑字段,均为可选,未提交字段保持不变。 */
export type PhotoReportUpdate = {
  title?: string | null;
  inspection_unit?: string | null;
  inspection_address?: string | null;
  violation_summary?: string | null;
  status?: RecordStatus;
  images?: PhotoReportImageUpdate[];
};

const base = "/api/photo-report";

export const photoReportService = {
  generate: (form: FormData) => api.post<GenerateResponse>(`${base}/generate`, form),
  list: (params: ListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<PhotoReportListItem>>(base, {
      query: { page: params.page, page_size: params.page_size, status: params.status },
      signal,
    }),
  get: (id: string, signal?: AbortSignal) =>
    api.get<PhotoReportDetail>(`${base}/${encodeURIComponent(id)}`, { signal }),
  update: (id: string, patch: PhotoReportUpdate) =>
    api.put<PhotoReportDetail>(`${base}/${encodeURIComponent(id)}`, patch),
  /** 下载 Word 文书(文件流);文档未生成返回 409,由 api-client 转为 ApiError。 */
  download: (id: string) =>
    api.get<Blob>(`${base}/${encodeURIComponent(id)}/download`, { responseType: "blob" }),
};
