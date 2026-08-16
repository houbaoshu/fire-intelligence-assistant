import { api } from "../api-client";

export type RecordGroupStats = {
  total: number;
  by_status: Record<string, number>;
};

export type Statistics = {
  scope: "personal" | "team" | "organization" | "system";
  generated_at: string;
  records: {
    inspection_records: RecordGroupStats;
    photo_reports: RecordGroupStats;
    interview_records: RecordGroupStats;
  };
  tasks: RecordGroupStats;
  knowledge: {
    document_count: number;
    indexed_count: number;
    indexing_count: number;
    failed_count: number;
    last_indexed_at: string | null;
  };
  generated_documents: { total: number };
};

export const SCOPE_LABELS: Record<string, string> = {
  personal: "我的数据",
  team: "团队数据",
  organization: "组织数据",
  system: "系统数据",
};

export const statisticsService = {
  get: (signal?: AbortSignal) => api.get<Statistics>("/api/statistics", { signal }),
};
