import { api } from "../api-client";

/**
 * The backend statistics schema is not yet fixed. The frontend treats each
 * value as an opaque number/string; missing fields render as "unavailable".
 */
export type Statistics = Record<string, number | string | null | undefined>;

export const statisticsService = {
  get: (signal?: AbortSignal) => api.get<Statistics>("/api/statistics", { signal }),
};
