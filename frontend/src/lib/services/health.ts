import { api } from "../api-client";

export type HealthStatus = { status: string };

export const healthService = {
  check: (signal?: AbortSignal) => api.get<HealthStatus>("/health", { anonymous: true, signal }),
};
