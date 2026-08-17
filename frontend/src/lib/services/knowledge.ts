import { api } from "../api-client";
import type { Paginated } from "./common";

/**
 * 知识库服务：严格对齐 docs/API.md §6。
 * 字段定义权在 docs/DATABASE.md knowledge_documents 表;前端不得假设契约之外的字段。
 */

/** 文档索引状态枚举(定义权:docs/DATABASE.md knowledge_documents.status)。 */
export type KnowledgeDocumentStatus =
  | "uploaded"
  | "parsing"
  | "indexing"
  | "indexed"
  | "failed"
  | "outdated";

export const KNOWLEDGE_DOCUMENT_STATUSES: KnowledgeDocumentStatus[] = [
  "uploaded",
  "parsing",
  "indexing",
  "indexed",
  "failed",
  "outdated",
];

/** 文档列表元素(API.md §6)。 */
export type KnowledgeDocument = {
  id: string;
  title: string;
  document_type: string | null;
  status: KnowledgeDocumentStatus;
  version: string | null;
  issuing_authority: string | null;
  effective_date: string | null;
  expiration_date: string | null;
  chunk_count: number | null;
  created_at: string;
  updated_at: string;
};

/** 列表查询参数(page 默认 1,page_size 默认 20;status 可选过滤)。 */
export type KnowledgeListParams = {
  page?: number;
  page_size?: number;
  status?: KnowledgeDocumentStatus;
};

/** POST /api/knowledge/documents 响应:解析与索引为异步任务(knowledge_indexing)。 */
export type KnowledgeUploadResponse = {
  document_id: string;
  task_id: string;
};

/** DELETE /api/knowledge/documents/{id} 响应。 */
export type KnowledgeDeleteResponse = {
  id: string;
  deleted: boolean;
};

/** POST /api/knowledge/rebuild 响应:全量重建为异步任务(knowledge_reindexing)。 */
export type KnowledgeRebuildResponse = {
  task_id: string;
};

/** GET /api/knowledge/status 响应:知识库聚合计数;尚无文档时计数为 0、last_indexed_at 为 null。 */
export type KnowledgeStatus = {
  document_count: number;
  indexed_count: number;
  indexing_count: number;
  failed_count: number;
  last_indexed_at: string | null;
};

const base = "/api/knowledge";

export const knowledgeService = {
  list: (params: KnowledgeListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<KnowledgeDocument>>(`${base}/documents`, {
      query: { page: params.page, page_size: params.page_size, status: params.status },
      signal,
    }),
  /** 上传知识库源文档(multipart/form-data,字段 file);类型与大小限制见 API.md §9。 */
  upload: (form: FormData) => api.post<KnowledgeUploadResponse>(`${base}/documents`, form),
  /** 软删除文档并移除其索引数据。 */
  remove: (id: string) =>
    api.delete<KnowledgeDeleteResponse>(`${base}/documents/${encodeURIComponent(id)}`),
  /** 触发全量索引重建(异步任务)。 */
  rebuild: () => api.post<KnowledgeRebuildResponse>(`${base}/rebuild`),
  /** 知识库聚合计数。 */
  status: (signal?: AbortSignal) => api.get<KnowledgeStatus>(`${base}/status`, { signal }),
};
