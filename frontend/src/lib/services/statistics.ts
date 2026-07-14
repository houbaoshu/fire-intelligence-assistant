import { api } from "../api-client";

export type Metric = {
  id: string;
  label: string;
  value: number | null;
  unit: string;
  available: boolean;
};

export type Statistics = {
  scope: "personal" | "organization" | "system";
  period_start: string | null;
  period_end: string;
  timezone: string;
  last_updated_at: string;
  metrics: Metric[];
  task_statuses: Record<string, number>;
  knowledge_statuses: Record<string, number>;
};

export const statisticsService = {
  get: (signal?: AbortSignal) => api.get<Statistics>("/api/statistics", { signal }),
};
