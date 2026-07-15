import { api } from "../api-client";

export type KnowledgeDocument = {
  id: string;
  title: string;
  name: string;
  document_type?: string | null;
  status: "uploaded" | "parsing" | "indexing" | "indexed" | "failed" | "outdated";
  version?: string | null;
  issuing_authority?: string | null;
  effective_date?: string | null;
  expiration_date?: string | null;
  chunk_count?: number | null;
  error?: string | null;
  task_id?: string | null;
  created_at: string;
  updated_at: string;
};

export const knowledgeService = {
  list: (signal?: AbortSignal) =>
    api.get<KnowledgeDocument[]>("/api/knowledge/documents", { signal }),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post<{ document: KnowledgeDocument; task_id: string }>(
      "/api/knowledge/documents",
      fd,
    );
  },
  delete: (id: string) =>
    api.delete<void>(`/api/knowledge/documents/${id}`, { responseType: "none" }),
  rebuild: () => api.post<{ task_id: string }>("/api/knowledge/rebuild"),
};
