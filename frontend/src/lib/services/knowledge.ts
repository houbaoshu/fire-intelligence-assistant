import { api } from "../api-client";

export type KnowledgeDocument = {
  id: string;
  name: string;
  size?: number;
  content_type?: string;
  status?: "pending" | "parsing" | "indexing" | "ready" | "failed" | string;
  error?: string | null;
  created_at?: string;
  updated_at?: string;
  [k: string]: unknown;
};

export const knowledgeService = {
  list: (signal?: AbortSignal) =>
    api.get<KnowledgeDocument[]>("/api/knowledge/documents", { signal }),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post<KnowledgeDocument>("/api/knowledge/documents", fd);
  },
  delete: (id: string) => api.delete<void>(`/api/knowledge/documents/${id}`, { responseType: "none" }),
  rebuild: () => api.post<{ task_id?: string } | void>("/api/knowledge/rebuild"),
};
