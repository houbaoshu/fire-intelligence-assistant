import { useQuery } from "@tanstack/react-query";
import { taskService, isTerminalTaskState, type TaskState } from "@/lib/services/tasks";

export function useTaskProgress(
  taskId: string | null | undefined,
  options?: { intervalMs?: number },
) {
  const interval = options?.intervalMs ?? 2000;
  const query = useQuery({
    queryKey: ["task", taskId],
    queryFn: ({ signal }) => taskService.get(taskId!, signal),
    enabled: !!taskId,
    refetchInterval: (q) => {
      const data = q.state.data as TaskState | undefined;
      if (!data) return interval;
      return isTerminalTaskState(data.status) ? false : interval;
    },
    retry: 1,
  });
  return {
    task: query.data,
    error: query.error,
    isLoading: query.isLoading,
    refetch: query.refetch,
  };
}
