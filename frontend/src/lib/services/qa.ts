import { api } from "../api-client";

/**
 * 法规问答服务：严格对齐 docs/API.md §5。
 * sources 元素字段以契约为准,前端不得假设后端返回其他字段;
 * 无可靠来源时 sources 为空数组(后端不得编造引用)。
 */

/** 来源引用(API.md §5);元数据字段可能缺失,展示时逐项判空。 */
export type SourceCitation = {
  document_id: string;
  title: string;
  article: string | null;
  page: number | null;
  excerpt: string;
  effective_date: string | null;
};

/** POST /api/qa/query 响应。 */
export type QAResponse = {
  answer: string;
  sources: SourceCitation[];
};

export const qaService = {
  /** 提交问题,返回基于 RAG 检索的回答与来源列表。 */
  query: (question: string, signal?: AbortSignal) =>
    api.post<QAResponse>("/api/qa/query", { question }, { signal }),
};
