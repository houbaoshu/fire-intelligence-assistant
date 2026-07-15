import { CheckCircle2, XCircle, Loader2, Clock, Ban } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useTaskProgress } from "@/hooks/useTaskProgress";
import type { TaskState, TaskStatus } from "@/lib/services/tasks";
import { cn } from "@/lib/utils";
import { useEffect, useRef, type ReactNode } from "react";

const LABELS: Record<TaskStatus, string> = {
  pending: "等待中",
  queued: "已排队",
  processing: "处理中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

function StatusIcon({ status }: { status: TaskStatus }) {
  const cls = "h-4 w-4";
  switch (status) {
    case "completed":
      return <CheckCircle2 className={cn(cls, "text-emerald-600")} />;
    case "failed":
      return <XCircle className={cn(cls, "text-destructive")} />;
    case "cancelled":
      return <Ban className={cn(cls, "text-muted-foreground")} />;
    case "processing":
      return <Loader2 className={cn(cls, "animate-spin text-primary")} />;
    default:
      return <Clock className={cn(cls, "text-muted-foreground")} />;
  }
}

export type TaskProgressProps = {
  taskId: string | null | undefined;
  intervalMs?: number;
  onComplete?: (task: TaskState) => void;
  onFail?: (task: TaskState) => void;
  className?: string;
  footer?: ReactNode;
};

export function TaskProgress({
  taskId,
  intervalMs,
  onComplete,
  onFail,
  className,
  footer,
}: TaskProgressProps) {
  const { task, error, isLoading } = useTaskProgress(taskId, { intervalMs });
  const notified = useRef<string | null>(null);

  useEffect(() => {
    if (!task || !["completed", "failed"].includes(task.status)) return;
    const key = `${task.id}:${task.attempt}:${task.status}`;
    if (notified.current === key) return;
    notified.current = key;
    if (task.status === "completed") onComplete?.(task);
    if (task.status === "failed") onFail?.(task);
  }, [onComplete, onFail, task]);

  if (!taskId) return null;

  return (
    <div className={cn("rounded-lg border border-border bg-card p-4", className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {task ? (
            <StatusIcon status={task.status} />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin" />
          )}
          <div className="text-sm font-medium">
            {task ? (LABELS[task.status] ?? task.status) : "查询任务状态…"}
          </div>
        </div>
        <Badge variant="outline" className="font-mono text-[10px]">
          {taskId.slice(0, 8)}
        </Badge>
      </div>

      {typeof task?.progress === "number" && (
        <div className="mt-3 space-y-1">
          <Progress value={Math.max(0, Math.min(100, task.progress))} />
          <div className="text-right text-xs text-muted-foreground">{task.progress}%</div>
        </div>
      )}

      {(task?.current_stage || task?.message) && (
        <div className="mt-2 text-xs text-muted-foreground">
          {task.current_stage || task.message}
        </div>
      )}

      {task?.error_message && (
        <div className="mt-2 text-xs text-destructive">{task.error_message}</div>
      )}

      {error && (
        <div className="mt-2 text-xs text-destructive">
          任务状态查询失败:{error instanceof Error ? error.message : String(error)}
        </div>
      )}

      {isLoading && !task && (
        <div className="mt-2 text-xs text-muted-foreground">正在连接后端…</div>
      )}

      {footer && <div className="mt-3">{footer}</div>}
    </div>
  );
}
