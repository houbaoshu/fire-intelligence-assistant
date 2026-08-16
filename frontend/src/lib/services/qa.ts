import { api } from "../api-client";

export type QASource = {
  document_id: string;
  title: string;
  article: string | null;
  page: number | null;
  excerpt: string | null;
  effective_date: string | null;
  issuing_authority: string | null;
  version: string | null;
  document_type: string | null;
};

export type QAAnswer = {
  answer: string;
  sources: QASource[];
};

export const qaService = {
  ask: (question: string, signal?: AbortSignal) =>
    api.post<QAAnswer>("/api/qa/query", { question }, { signal }),
};
