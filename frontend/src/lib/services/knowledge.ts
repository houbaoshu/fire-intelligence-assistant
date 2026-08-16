import { api, API_BASE_URL } from "../api-client";

export type KnowledgeDocument = {
  id: string;
  title: string;
  document_type: string | null;
  status: "uploaded" | "parsing" | "indexing" | "indexed" | "failed" | "outdated";
  version: string | null;
  issuing_authority: string | null;
  effective_date: string | null;
  chunk_count: number | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeListResponse = {
  items: KnowledgeDocument[];
  total: number;
  page: number;
  page_size: number;
};

export type KnowledgeStatus = {
  document_count: number;
  indexed_count: number;
  indexing_count: number;
  failed_count: number;
  last_indexed_at: string | null;
};

export type KnowledgeUploadResponse = {
  document_id: string;
  task_id: string;
};

export const KNOWLEDGE_STATUS_LABELS: Record<string, string> = {
  uploaded: "已上传",
  parsing: "解析中",
  indexing: "索引中",
  indexed: "已索引",
  failed: "失败",
  outdated: "已失效",
};

export const knowledgeService = {
  list: (
    params: { page?: number; page_size?: number; status?: string } = {},
    signal?: AbortSignal,
  ) => api.get<KnowledgeListResponse>("/api/knowledge/documents", { query: params, signal }),
  upload: (file: File, title?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    return api.post<KnowledgeUploadResponse>("/api/knowledge/documents", fd);
  },
  delete: (id: string) =>
    api.delete<{ id: string; deleted: boolean }>(
      "/api/knowledge/documents/" + encodeURIComponent(id),
    ),
  rebuild: () => api.post<{ task_id: string }>("/api/knowledge/rebuild"),
  status: (signal?: AbortSignal) => api.get<KnowledgeStatus>("/api/knowledge/status", { signal }),
  sourceUrl: (id: string) =>
    API_BASE_URL + "/api/knowledge/documents/" + encodeURIComponent(id) + "/source",
};
