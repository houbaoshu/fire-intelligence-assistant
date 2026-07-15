import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, RefreshCw, RotateCcw } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { PageHeader } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { taskService } from "@/lib/services/tasks";

export const Route = createFileRoute("/tasks")({
  head: () => ({ meta: [{ title: "任务中心 · 消防智能助手" }] }),
  component: TasksPage,
});

function TasksPage() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["tasks"],
    queryFn: ({ signal }) => taskService.list(signal),
  });
  const retry = useMutation({
    mutationFn: taskService.retry,
    onSuccess: () => client.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const cancel = useMutation({
    mutationFn: taskService.cancel,
    onSuccess: () => client.invalidateQueries({ queryKey: ["tasks"] }),
  });
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="任务中心"
        description="查看授权范围内的处理状态；重试和取消都由后端校验当前状态。"
        actions={
          <Button variant="outline" onClick={() => query.refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
        }
      />
      {query.isLoading ? (
        <LoadingState />
      ) : query.error ? (
        <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
      ) : (
        <div className="space-y-3">
          {query.data?.items.map((task) => (
            <Card key={task.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{task.task_type}</span>
                    <Badge variant="outline">{task.status}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {task.current_stage || "暂无阶段"} · {task.progress}% ·{" "}
                    {new Date(task.updated_at).toLocaleString()}
                  </p>
                  {task.error_message && (
                    <p className="mt-1 text-xs text-destructive">{task.error_message}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  {["failed", "cancelled"].includes(task.status) && (
                    <Button size="sm" variant="outline" onClick={() => retry.mutate(task.id)}>
                      <RotateCcw className="mr-1 h-4 w-4" />
                      重试
                    </Button>
                  )}
                  {["pending", "queued", "processing"].includes(task.status) && (
                    <Button size="sm" variant="outline" onClick={() => cancel.mutate(task.id)}>
                      <Ban className="mr-1 h-4 w-4" />
                      取消
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
