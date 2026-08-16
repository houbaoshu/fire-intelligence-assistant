import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, CheckCircle2, Loader2, RefreshCw, RotateCcw, XCircle, Clock } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import {
  taskService,
  TASK_STATUS_LABELS,
  TASK_TYPE_LABELS,
  type TaskOut,
  type TaskStatus,
} from "@/lib/services/tasks";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/tasks")({
  head: () => ({
    meta: [
      { title: "任务中心 · 消防智能助手" },
      { name: "description", content: "查看、重试与取消异步 AI 任务。" },
    ],
  }),
  component: TasksPage,
});

const STATUSES: TaskStatus[] = [
  "pending",
  "queued",
  "processing",
  "completed",
  "failed",
  "cancelled",
];

const STATUS_TONE: Record<string, string> = {
  pending: "bg-muted text-muted-foreground",
  queued: "bg-amber-500/15 text-amber-700",
  processing: "bg-blue-500/15 text-blue-600",
  completed: "bg-emerald-500/15 text-emerald-700",
  failed: "bg-destructive/15 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
};

function TasksPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [taskType, setTaskType] = useState("");

  const query = useQuery({
    queryKey: ["tasks", { status, taskType }],
    queryFn: ({ signal }) =>
      taskService.list(
        { limit: 50, status: status || undefined, task_type: taskType || undefined },
        signal,
      ),
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => taskService.retry(id),
    onSuccess: () => {
      toast.success("已创建重试任务");
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (e) => toast.error("重试失败:" + e.message),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => taskService.cancel(id),
    onSuccess: () => {
      toast.success("已取消任务");
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (e) => toast.error("取消失败:" + e.message),
  });

  const goToRecord = (task: TaskOut) => {
    const recordId = task.result_data?.record_id;
    if (typeof recordId !== "string") return;
    const target = {
      inspection_record_generation: "/inspection-record",
      photo_report_generation: "/photo-report",
      interview_record_generation: "/interview-record",
    }[task.task_type];
    if (target) navigate({ to: target as never, search: { id: recordId } as never });
  };

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="任务中心"
        description="跟踪所有异步 AI 任务:生成、索引与文书渲染。失败任务可重试,进行中任务可取消。"
      />
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">任务列表</CardTitle>
          <div className="flex items-center gap-2">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-md border border-input bg-background px-2 py-1 text-sm"
            >
              <option value="">全部状态</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {TASK_STATUS_LABELS[s] ?? s}
                </option>
              ))}
            </select>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="rounded-md border border-input bg-background px-2 py-1 text-sm"
            >
              <option value="">全部类型</option>
              {Object.entries(TASK_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")}
              />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {query.isLoading ? (
            <LoadingState description="正在加载任务…" />
          ) : query.isError ? (
            <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
          ) : query.data && query.data.items.length === 0 ? (
            <EmptyState title="暂无任务" description="提交生成任务后会显示在这里。" />
          ) : (
            <div className="divide-y">
              {query.data?.items.map((task) => (
                <TaskRow
                  key={task.task_id}
                  task={task}
                  onRetry={() => retryMutation.mutate(task.task_id)}
                  onCancel={() => cancelMutation.mutate(task.task_id)}
                  onOpenRecord={() => goToRecord(task)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-destructive" />;
    case "cancelled":
      return <Ban className="h-4 w-4 text-muted-foreground" />;
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function TaskRow({
  task,
  onRetry,
  onCancel,
  onOpenRecord,
}: {
  task: TaskOut;
  onRetry: () => void;
  onCancel: () => void;
  onOpenRecord: () => void;
}) {
  const canRetry = task.status === "failed" || task.status === "cancelled";
  const canCancel =
    task.status === "pending" || task.status === "queued" || task.status === "processing";
  const hasRecord = typeof task.result_data?.record_id === "string";

  return (
    <div className="py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <StatusIcon status={task.status} />
          <span className="text-sm font-medium">
            {TASK_TYPE_LABELS[task.task_type] ?? task.task_type}
          </span>
          <Badge variant="outline" className={STATUS_TONE[task.status] ?? ""}>
            {TASK_STATUS_LABELS[task.status] ?? task.status}
          </Badge>
        </div>
        <span className="font-mono text-[10px] text-muted-foreground">
          {task.task_id.slice(0, 8)}
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {task.status === "processing" && (
          <span className="flex items-center gap-2">
            <span className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
              <span className="block h-full bg-primary" style={{ width: task.progress + "%" }} />
            </span>
            {task.progress}%{task.current_stage ? " · " + task.current_stage : ""}
          </span>
        )}
        <span>更新于 {new Date(task.updated_at).toLocaleString("zh-CN")}</span>
        {task.status === "failed" && task.error_message && (
          <span className="text-destructive">{task.error_message}</span>
        )}
      </div>
      {(canRetry || canCancel || hasRecord) && (
        <div className="mt-2 flex gap-2">
          {canRetry && (
            <Button size="sm" variant="outline" onClick={onRetry}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> 重试
            </Button>
          )}
          {canCancel && (
            <Button size="sm" variant="outline" onClick={onCancel}>
              <Ban className="mr-1.5 h-3.5 w-3.5" /> 取消
            </Button>
          )}
          {hasRecord && (
            <Button size="sm" variant="ghost" onClick={onOpenRecord}>
              查看关联记录
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
