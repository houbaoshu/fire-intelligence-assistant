import { useQuery } from "@tanstack/react-query";
import { healthService } from "@/lib/services/health";
import { isApiConfigured } from "@/lib/api-client";

export type BackendHealth =
  | { state: "unconfigured" }
  | { state: "checking" }
  | { state: "connected"; raw: unknown }
  | { state: "disconnected"; error: string };

export function useBackendHealth(options?: { refetchInterval?: number }) {
  const configured = isApiConfigured();
  const query = useQuery({
    queryKey: ["backend-health"],
    queryFn: ({ signal }) => healthService.check(signal),
    enabled: configured,
    retry: 0,
    refetchInterval: options?.refetchInterval,
    staleTime: 15_000,
  });

  let health: BackendHealth;
  if (!configured) health = { state: "unconfigured" };
  else if (query.isLoading || query.isFetching && !query.data && !query.error)
    health = { state: "checking" };
  else if (query.error)
    health = {
      state: "disconnected",
      error: query.error instanceof Error ? query.error.message : "Unknown error",
    };
  else if (query.data) health = { state: "connected", raw: query.data };
  else health = { state: "checking" };

  return { health, refetch: query.refetch, isFetching: query.isFetching };
}
