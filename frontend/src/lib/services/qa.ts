import { api } from "../api-client";

export type QAAnswer = {
  answer: string;
  evidence_status: "grounded" | "no_evidence" | "retrieval_only";
  sources: Array<{
    document_id: string;
    title: string;
    issuing_authority?: string | null;
    version?: string | null;
    effective_date?: string | null;
    article?: string | null;
    page?: number | null;
    excerpt: string;
    snippet: string;
  }>;
};

export const qaService = {
  ask: (question: string, signal?: AbortSignal) =>
    api.post<QAAnswer>("/api/qa/query", { question }, { signal }),
};
