import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { RefreshCw, RotateCcw, Ban, ListChecks } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { TaskStatusBadge } from "@/components/common/StatusBadges";
import { TaskRecordLink } from "@/components/common/TaskRecordLink";
import { ApiError } from "@/lib/api-client";
import { useTaskProgress } from "@/hooks/useTaskProgress";
import {
  taskService,
  isTerminalTaskState,
  type Task,
  type TaskStatus,
  type TaskType,
} from "@/lib/services/tasks";
import { TASK_STAGE_LABELS, TASK_STATUS_LABELS, TASK_TYPE_LABELS, labelOf } from "@/lib/labels";
import { formatDateTime, formatDuration } from "@/lib/datetime";

export const Route = createFileRoute("/tasks")({
  head: () => ({
    meta: [
      { title: "任务中心 · 消防智能助手" },
      { name: "description", content: "查看异步任务进度与结果,按状态与类型过滤,支持重试与取消。" },
    ],
  }),
  component: TaskCenterPage,
});

const ALL = "__all__";
const STATUS_OPTIONS: TaskStatus[] = [
  "pending",
  "queued",
  "processing",
  "completed",
  "failed",
  "cancelled",
];
const TYPE_OPTIONS: TaskType[] = [
  "inspection_record_generation",
  "photo_report_generation",
  "interview_record_generation",
  "speech_transcription",
  "video_analysis",
  "document_generation",
  "knowledge_indexing",
  "knowledge_reindexing",
];
const LIMIT_OPTIONS = [20, 50, 100] as const;

/** 进行中任务的行内轮询间隔;整列表轻量刷新间隔。 */
const ROW_POLL_INTERVAL_MS = 3000;
const LIST_POLL_INTERVAL_MS = 10_000;

/** 统一可读错误;409 状态冲突由后端返回可读 message,原样展示。 */
function readableError(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return `没有权限执行此操作(${e.message})`;
    return e.message;
  }
  return e instanceof Error ? e.message : fallback;
}

type PendingAction = { kind: "retry" | "cancel"; task: Task } | { kind: "retry_all" };

/** 任务到达终态时的播报文案(仅播报有意义的状态变化,见 specs/workflow.md §6)。 */
function terminalAnnouncement(task: Task): string {
  const type = labelOf(TASK_TYPE_LABELS, task.task_type);
  if (task.status === "completed") return `${type}任务已完成`;
  if (task.status === "failed") return `${type}任务失败`;
  return `${type}任务已取消`;
}

function TaskRow({
  task,
  actionPending,
  onAction,
  onTerminal,
}: {
  task: Task;
  actionPending: boolean;
  onAction: (action: PendingAction) => void;
  onTerminal: (task: Task) => void;
}) {
  // 行内轮询:进行中任务单独轮询,到达终态自动停止(useTaskProgress 内部判断)。
  const { task: live } = useTaskProgress(isTerminalTaskState(task.status) ? null : task.task_id, {
    intervalMs: ROW_POLL_INTERVAL_MS,
  });
  const current = live ?? task;

  const notifiedRef = useRef(false);
  useEffect(() => {
    if (live && isTerminalTaskState(live.status) && !notifiedRef.current) {
      notifiedRef.current = true;
      onTerminal(live);
    }
  }, [live, onTerminal]);

  const terminal = isTerminalTaskState(current.status);
  const canRetry = current.status === "failed" || current.status === "cancelled";
  const canCancel =
    current.status === "pending" || current.status === "queued" || current.status === "processing";
  const showProgress = typeof current.progress === "number" && !terminal;

  return (
    <TableRow>
      <TableCell>
        <TaskStatusBadge status={current.status} />
      </TableCell>
      <TableCell className="text-sm">
        <div>{labelOf(TASK_TYPE_LABELS, current.task_type)}</div>
        {current.status === "failed" && current.error_message && (
          <div className="mt-1 max-w-64 text-xs text-destructive">{current.error_message}</div>
        )}
      </TableCell>
      <TableCell>
        {showProgress ? (
          <div className="flex w-28 flex-col gap-1">
            <Progress value={Math.max(0, Math.min(100, current.progress ?? 0))} />
            <span className="text-right text-xs text-muted-foreground">{current.progress}%</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">
        {labelOf(TASK_STAGE_LABELS, current.current_stage)}
      </TableCell>
      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
        {terminal
          ? `耗时 ${formatDuration(
              new Date(current.updated_at).getTime() - new Date(current.created_at).getTime(),
            )}`
          : `更新于 ${formatDateTime(current.updated_at)}`}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <TaskRecordLink task={current} />
          {canRetry && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs"
              disabled={actionPending}
              onClick={() => onAction({ kind: "retry", task: current })}
            >
              <RotateCcw className="mr-1 h-3 w-3" /> 重试
            </Button>
          )}
          {canCancel && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs"
              disabled={actionPending}
              onClick={() => onAction({ kind: "cancel", task: current })}
            >
              <Ban className="mr-1 h-3 w-3" /> 取消
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

function TaskCenterPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TaskStatus | undefined>(undefined);
  const [typeFilter, setTypeFilter] = useState<TaskType | undefined>(undefined);
  const [limit, setLimit] = useState<number>(20);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [announcement, setAnnouncement] = useState("");

  const invalidateAll = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    void queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }, [queryClient]);

  // 状态过滤由后端支持(status 参数,API.md §8);类型过滤契约暂无参数,在当前结果集内客户端过滤。
  const listQuery = useQuery({
    queryKey: ["tasks", "center", { status: statusFilter, limit }],
    queryFn: ({ signal }) => taskService.list({ status: statusFilter, limit }, signal),
    retry: 1,
    refetchInterval: (q) => {
      const items = q.state.data?.items;
      return items?.some((t) => !isTerminalTaskState(t.status)) ? LIST_POLL_INTERVAL_MS : false;
    },
  });

  const items = listQuery.data?.items ?? [];
  const visibleItems = typeFilter ? items.filter((t) => t.task_type === typeFilter) : items;
  const failedItems = visibleItems.filter((t) => t.status === "failed");

  // 行内任务到达终态:刷新列表与通知,并通过 aria-live 播报一次。
  const handleTerminal = useCallback(
    (task: Task) => {
      setAnnouncement(terminalAnnouncement(task));
      invalidateAll();
    },
    [invalidateAll],
  );

  const retryMutation = useMutation({
    mutationFn: (taskId: string) => taskService.retry(taskId),
    onSuccess: () => {
      toast.success("已创建重试任务");
      invalidateAll();
    },
    onError: (err) => {
      toast.error(readableError(err, "重试失败"));
      // 409 状态冲突等场景刷新列表,确保展示真实状态。
      invalidateAll();
    },
    onSettled: () => setPendingAction(null),
  });

  const cancelMutation = useMutation({
    mutationFn: (taskId: string) => taskService.cancel(taskId),
    onSuccess: () => {
      toast.success("任务已取消");
      invalidateAll();
    },
    onError: (err) => {
      toast.error(readableError(err, "取消失败"));
      invalidateAll();
    },
    onSettled: () => setPendingAction(null),
  });

  // 批量重试:客户端逐个调用 retry(不新增后端端点),汇总成功/失败反馈。
  const batchRetryMutation = useMutation({
    mutationFn: async (tasks: Task[]) => {
      let succeeded = 0;
      const failures: string[] = [];
      for (const t of tasks) {
        try {
          await taskService.retry(t.task_id);
          succeeded += 1;
        } catch (err) {
          failures.push(readableError(err, "重试失败"));
        }
      }
      return { succeeded, failures };
    },
    onSuccess: ({ succeeded, failures }) => {
      if (failures.length === 0) {
        toast.success(`批量重试完成,已重试 ${succeeded} 项任务`);
      } else {
        toast.error(`批量重试完成:成功 ${succeeded} 项,失败 ${failures.length} 项(${failures[0]})`);
      }
      invalidateAll();
    },
    onSettled: () => setPendingAction(null),
  });

  const actionPending =
    retryMutation.isPending || cancelMutation.isPending || batchRetryMutation.isPending;

  const confirmAction = () => {
    if (!pendingAction) return;
    if (pendingAction.kind === "retry") retryMutation.mutate(pendingAction.task.task_id);
    else if (pendingAction.kind === "cancel") cancelMutation.mutate(pendingAction.task.task_id);
    else batchRetryMutation.mutate(failedItems);
  };

  const actionLabel = (a: PendingAction) =>
    a.kind === "cancel" ? "取消" : a.kind === "retry" ? "重试" : "批量重试";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="任务中心"
        description="查看异步任务的进度、阶段与结果;失败任务可重试,进行中任务可取消。"
      />

      {/* 仅播报任务进入终态等有意义的状态变化,轮询刷新不播报(specs/workflow.md §6/§13)。 */}
      <div aria-live="polite" role="status" className="sr-only">
        {announcement}
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">任务列表</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={statusFilter ?? ALL}
              onValueChange={(v) => setStatusFilter(v === ALL ? undefined : (v as TaskStatus))}
            >
              <SelectTrigger className="h-8 w-32" aria-label="按任务状态过滤">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>全部状态</SelectItem>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {TASK_STATUS_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={typeFilter ?? ALL}
              onValueChange={(v) => setTypeFilter(v === ALL ? undefined : (v as TaskType))}
            >
              <SelectTrigger className="h-8 w-40" aria-label="按任务类型过滤">
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>全部类型</SelectItem>
                {TYPE_OPTIONS.map((t) => (
                  <SelectItem key={t} value={t}>
                    {TASK_TYPE_LABELS[t]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
              <SelectTrigger className="h-8 w-28" aria-label="每页条数">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LIMIT_OPTIONS.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n} 条
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {failedItems.length > 0 && (
              <Button
                size="sm"
                variant="outline"
                className="h-8"
                disabled={actionPending}
                onClick={() => setPendingAction({ kind: "retry_all" })}
              >
                <RotateCcw className="mr-1 h-3.5 w-3.5" />
                批量重试({failedItems.length})
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => listQuery.refetch()}
              disabled={listQuery.isFetching}
            >
              <RefreshCw
                className={`mr-2 h-3.5 w-3.5 ${listQuery.isFetching ? "animate-spin" : ""}`}
              />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.error ? (
            <ErrorState
              description={readableError(listQuery.error, "加载失败")}
              onRetry={() => listQuery.refetch()}
            />
          ) : visibleItems.length === 0 ? (
            <EmptyState
              title="暂无任务"
              description={
                statusFilter || typeFilter
                  ? "当前过滤条件下没有任务,可调整过滤条件查看。"
                  : "提交生成任务后,将在这里显示进度与结果。"
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>状态</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>进度</TableHead>
                    <TableHead>当前阶段</TableHead>
                    <TableHead>耗时 / 更新时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleItems.map((task) => (
                    <TaskRow
                      key={task.task_id}
                      task={task}
                      actionPending={actionPending}
                      onAction={setPendingAction}
                      onTerminal={handleTerminal}
                    />
                  ))}
                </TableBody>
              </Table>
              <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                <ListChecks className="h-3.5 w-3.5" />
                <span>
                  共 {listQuery.data?.total ?? visibleItems.length} 项任务,显示最近{" "}
                  {visibleItems.length} 项
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={pendingAction !== null}
        onOpenChange={(open) => !open && !actionPending && setPendingAction(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingAction ? `确认${actionLabel(pendingAction)}?` : ""}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingAction?.kind === "retry" &&
                `将重试「${labelOf(TASK_TYPE_LABELS, pendingAction.task.task_type)}」任务:后端会创建新的任务实例,原任务保留用于审计。`}
              {pendingAction?.kind === "cancel" &&
                `将取消「${labelOf(TASK_TYPE_LABELS, pendingAction.task.task_type)}」任务:取消为尽力而为,已提交的成果不会被隐式删除。`}
              {pendingAction?.kind === "retry_all" &&
                `将逐个重试当前列表中 ${failedItems.length} 项失败任务,每项都会创建新的任务实例。`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionPending}>返回</AlertDialogCancel>
            <AlertDialogAction
              disabled={actionPending}
              onClick={(e) => {
                e.preventDefault();
                confirmAction();
              }}
            >
              {actionPending ? "处理中…" : pendingAction ? `确认${actionLabel(pendingAction)}` : ""}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
