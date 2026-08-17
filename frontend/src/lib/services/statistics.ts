import { api } from "../api-client";

/**
 * 统计契约(API.md §7)。by_status 为稀疏键:某状态计数为 0 时键可省略,
 * 前端必须区分「零」「缺失」与「不可用」;指标族整体也可能缺失。
 */

export type StatisticsScope = "personal" | "team" | "organization" | "system";

export type RecordFamilyStats = {
  total: number;
  /** 稀疏键:仅包含有数据的状态。 */
  by_status: Record<string, number>;
};

export type TaskStats = {
  total: number;
  by_status: Record<string, number>;
};

export type KnowledgeStats = {
  document_count: number;
  indexed_count: number;
  indexing_count: number;
  failed_count: number;
};

export type Statistics = {
  scope: StatisticsScope;
  generated_at: string;
  records: {
    inspection_records?: RecordFamilyStats;
    photo_reports?: RecordFamilyStats;
    interview_records?: RecordFamilyStats;
  };
  tasks?: TaskStats;
  knowledge?: KnowledgeStats;
  generated_documents?: { total: number };
};

export const statisticsService = {
  get: (signal?: AbortSignal) => api.get<Statistics>("/api/statistics", { signal }),
};
