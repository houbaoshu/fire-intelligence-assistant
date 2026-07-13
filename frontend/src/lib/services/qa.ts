import { api } from "../api-client";

export type QAAnswer = {
  answer: string;
  sources: Array<{
    id?: string;
    title?: string;
    snippet?: string;
    url?: string;
    [k: string]: unknown;
  }>;
};

export const qaService = {
  ask: (question: string, signal?: AbortSignal) =>
    api.post<QAAnswer>("/api/qa/query", { question }, { signal }),
};
