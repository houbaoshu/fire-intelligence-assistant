import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  MessageSquareText,
  ClipboardList,
  Images,
  Mic,
  BookOpen,
  Settings as SettingsIcon,
  RotateCcw,
} from "lucide-react";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/AppShell";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { statisticsService, type RecordFamilyStats } from "@/lib/services/statistics";
import { taskService, type Task } from "@/lib/services/tasks";
import {
  RECORD_STATUS_LABELS,
  SCOPE_LABELS,
  TASK_STATUS_LABELS,
  TASK_TYPE_LABELS,
  labelOf,
} from "@/lib/labels";
import { formatDateTime } from "@/lib/datetime";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "工作台 · 消防智能助手" },
      { name: "description", content: "查看后端连接状态、统计数据与最近任务,快速进入各模块。" },
    ],
  }),
  component: Dashboard,
});

const SHORTCUTS = [
  { to: "/regulation-qa", label: "法规问答", icon: MessageSquareText },
  { to: "/inspection-record", label: "检查记录", icon: ClipboardList },
  { to: "/photo-report", label: "图像报告", icon: Images },
  { to: "/interview-record", label: "询问笔录", icon: Mic },
  { to: "/knowledge-base", label: "知识库", icon: BookOpen },
  { to: "/settings", label: "设置", icon: SettingsIcon },
] as const;

/** 「零」「缺失」「不可用」三态区分(specs/dashboard.md):确认无数据为 0,键省略为缺失,异常值为不可用。 */
function CountValue({ value }: { value: number | undefined }) {
  if (value === undefined) return <span className="text-muted-foreground">缺失</span>;
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
    return <span className="text-muted-foreground">不可用</span>;
  return <span className="text-2xl font-semibold tracking-tight">{value}</span>;
}

function StatusChips({
  byStatus,
  labels,
}: {
  byStatus: Record<string, number> | undefined;
  labels: Record<string, string>;
}) {
  if (!byStatus || Object.keys(byStatus).length === 0)
    return <span className="text-xs text-muted-foreground">无状态分布数据</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(byStatus).map(([status, count]) => (
        <Badge key={status} variant="outline" className="text-[10px]">
          {labelOf(labels, status)} {count}
        </Badge>
      ))}
    </div>
  );
}

function StatCard({
  title,
  family,
  labels,
  footer,
}: {
  title: string;
  family: RecordFamilyStats | { total: number } | undefined;
  labels?: Record<string, string>;
  footer?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {family === undefined ? (
          <span className="text-sm text-muted-foreground">该指标缺失</span>
        ) : (
          <>
            <CountValue value={family.total} />
            {labels && "by_status" in family && (
              <StatusChips byStatus={family.by_status} labels={labels} />
            )}
            {footer}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/** 已完成的生成类任务的安全导航:按 task_type 链接到对应记录详情(共享实现见 TaskRecordLink)。 */
function RecordLink({ task }: { task: Task }) {
  return <TaskRecordLink task={task} />;
}

function StatisticsSection() {
  const statsQuery = useQuery({
    queryKey: ["statistics"],
    queryFn: ({ signal }) => statisticsService.get(signal),
    retry: 1,
  });

  if (statsQuery.isLoading) return <LoadingState title="加载统计数据…" />;
  if (statsQuery.error)
    return (
      <ErrorState
        title="统计数据不可用"
        description={statsQuery.error instanceof Error ? statsQuery.error.message : "加载失败"}
        onRetry={() => statsQuery.refetch()}
      />
    );
  const stats = statsQuery.data;
  if (!stats) return <EmptyState title="暂无统计数据" />;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>
          数据范围:
          <span className="text-foreground">{labelOf(SCOPE_LABELS, stats.scope)}</span>
        </span>
        <span>统计时间:{formatDateTime(stats.generated_at)}</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="检查记录"
          family={stats.records.inspection_records}
          labels={RECORD_STATUS_LABELS}
        />
        <StatCard
          title="拍照报告"
          family={stats.records.photo_reports}
          labels={RECORD_STATUS_LABELS}
        />
        <StatCard
          title="询问记录"
          family={stats.records.interview_records}
          labels={RECORD_STATUS_LABELS}
        />
        <StatCard title="生成文书" family={stats.generated_documents} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">AI 任务状态分布</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {stats.tasks === undefined ? (
              <span className="text-sm text-muted-foreground">该指标缺失</span>
            ) : (
              <>
                <CountValue value={stats.tasks.total} />
                <StatusChips byStatus={stats.tasks.by_status} labels={TASK_STATUS_LABELS} />
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">知识库状态</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.knowledge === undefined ? (
              <span className="text-sm text-muted-foreground">该指标缺失</span>
            ) : (
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  文档总数:
                  <CountValue value={stats.knowledge.document_count} />
                </div>
                <div>
                  已索引:
                  <CountValue value={stats.knowledge.indexed_count} />
                </div>
                <div>
                  索引中:
                  <CountValue value={stats.knowledge.indexing_count} />
                </div>
                <div>
                  失败:
                  <CountValue value={stats.knowledge.failed_count} />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function RecentTasksSection() {
  const queryClient = useQueryClient();
  const tasksQuery = useQuery({
    queryKey: ["tasks", "recent"],
    queryFn: ({ signal }) => taskService.list({ limit: 10 }, signal),
    retry: 1,
  });
  const retryMutation = useMutation({
    mutationFn: (taskId: string) => taskService.retry(taskId),
    onSuccess: () => {
      toast.success("已创建重试任务");
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "重试失败");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">最近任务</CardTitle>
      </CardHeader>
      <CardContent>
        {tasksQuery.isLoading ? (
          <LoadingState />
        ) : tasksQuery.error ? (
          <ErrorState
            title="最近任务不可用"
            description={tasksQuery.error instanceof Error ? tasksQuery.error.message : "加载失败"}
            onRetry={() => tasksQuery.refetch()}
          />
        ) : !tasksQuery.data || tasksQuery.data.items.length === 0 ? (
          <EmptyState title="暂无任务" description="提交生成任务后,将在这里显示进度与结果。" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="hidden md:table-cell">更新时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasksQuery.data.items.map((task) => (
                <TableRow key={task.task_id}>
                  <TableCell className="text-sm">
                    <div>{labelOf(TASK_TYPE_LABELS, task.task_type)}</div>
                    {task.status === "failed" && task.error_message && (
                      <div className="mt-1 max-w-xs truncate text-xs text-destructive">
                        {task.error_message}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <TaskStatusBadge status={task.status} />
                  </TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground md:table-cell">
                    {formatDateTime(task.updated_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {task.status === "completed" && <RecordLink task={task} />}
                      {(task.status === "failed" || task.status === "cancelled") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-xs"
                          disabled={retryMutation.isPending}
                          onClick={() => retryMutation.mutate(task.task_id)}
                        >
                          <RotateCcw className="mr-1 h-3 w-3" /> 重试
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function Dashboard() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="工作台"
        description="查看系统状态、真实统计数据与最近任务,快速恢复工作。"
      />

      <BackendStatusCard />

      <section aria-label="统计概览">
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">统计概览</h2>
        <StatisticsSection />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentTasksSection />
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">快捷入口</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {SHORTCUTS.map((s) => (
                <Link
                  key={s.to}
                  to={s.to}
                  className="group flex items-center gap-3 rounded-lg border border-border bg-card p-3 transition hover:border-primary/50 hover:bg-accent/40"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <s.icon className="h-4 w-4" />
                  </div>
                  <div className="text-sm font-medium">{s.label}</div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
