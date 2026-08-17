import { useEffect } from "react";
import { CheckCircle2, XCircle, Loader2, Clock, Ban } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useTaskProgress } from "@/hooks/useTaskProgress";
import { TASK_STATUS_LABELS, labelOf } from "@/lib/labels";
import type { Task, TaskStatus } from "@/lib/services/tasks";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

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
  onComplete?: (task: Task) => void;
  onFail?: (task: Task) => void;
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

  // 终态回调在 effect 中触发(轮询停止后幂等),允许回调内安全执行导航等副作用。
  const status = task?.status;
  useEffect(() => {
    if (!task) return;
    if (status === "completed") onComplete?.(task);
    if (status === "failed") onFail?.(task);
    // 仅需在任务进入终态时触发一次;回调引用变化不重复触发。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, task?.task_id]);

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
            {task ? labelOf(TASK_STATUS_LABELS, task.status) : "查询任务状态…"}
          </div>
          {task?.current_stage && (
            <Badge variant="outline" className="text-[10px]">
              当前阶段:{task.current_stage}
            </Badge>
          )}
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

      {task?.status === "failed" && task.error_message && (
        <div className="mt-2 text-xs text-destructive">失败原因:{task.error_message}</div>
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
