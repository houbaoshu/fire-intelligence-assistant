import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  MessageSquareText,
  ClipboardList,
  Images,
  Mic,
  BookOpen,
  Settings as SettingsIcon,
  FileText,
  Brain,
  Database,
} from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { statisticsService, SCOPE_LABELS } from "@/lib/services/statistics";
import { taskService, TASK_STATUS_LABELS, TASK_TYPE_LABELS } from "@/lib/services/tasks";
import { knowledgeService, KNOWLEDGE_STATUS_LABELS } from "@/lib/services/knowledge";
import { RecordStatusBadge } from "@/components/common/RecordStatusBadge";
import { RECORD_STATUS_LABELS } from "@/lib/record-status";

export const Route = createFileRoute("/_authenticated/")({
  head: () => ({
    meta: [
      { title: "工作台 · 消防智能助手" },
      { name: "description", content: "查看后端连接状态、统计数据与最近任务。" },
    ],
  }),
  component: Dashboard,
});

const SHORTCUTS = [
  { to: "/regulation-qa", label: "法规问答", icon: MessageSquareText, desc: "检索法规并提问" },
  { to: "/inspection-record", label: "检查记录", icon: ClipboardList, desc: "视频生成检查记录" },
  { to: "/photo-report", label: "拍照报告", icon: Images, desc: "关键帧生成照片报告" },
  { to: "/interview-record", label: "询问笔录", icon: Mic, desc: "录音生成询问笔录" },
  { to: "/knowledge-base", label: "知识库", icon: BookOpen, desc: "管理法规文档" },
  { to: "/settings", label: "设置", icon: SettingsIcon, desc: "连接状态与偏好" },
] as const;

function Dashboard() {
  const statsQuery = useQuery({
    queryKey: ["statistics"],
    queryFn: ({ signal }) => statisticsService.get(signal),
  });
  const tasksQuery = useQuery({
    queryKey: ["recent-tasks"],
    queryFn: ({ signal }) => taskService.list({ limit: 8 }, signal),
  });
  const knowledgeQuery = useQuery({
    queryKey: ["knowledge-status"],
    queryFn: ({ signal }) => knowledgeService.status(signal),
  });

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="工作台" description="系统状态、真实统计数据与最近任务一览。" />

      <div className="grid gap-4 md:grid-cols-2">
        <BackendStatusCard />
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-sm">统计范围</CardTitle>
            {statsQuery.data && (
              <span className="text-xs text-muted-foreground">
                {SCOPE_LABELS[statsQuery.data.scope] ?? statsQuery.data.scope}
                {statsQuery.data.generated_at
                  ? " · 更新于 " +
                    new Date(statsQuery.data.generated_at).toLocaleTimeString("zh-CN")
                  : ""}
              </span>
            )}
          </CardHeader>
          <CardContent>
            <StatsBody query={statsQuery} />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <Brain className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">AI 任务</CardTitle>
          </CardHeader>
          <CardContent>
            <TasksBody query={tasksQuery} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm">知识库状态</CardTitle>
          </CardHeader>
          <CardContent>
            <KnowledgeBody query={knowledgeQuery} />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">快捷入口</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SHORTCUTS.map((s) => (
            <Link
              key={s.to}
              to={s.to}
              className="group flex items-center gap-3 rounded-lg border border-border bg-card p-4 transition hover:border-primary/50 hover:bg-accent/40"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                <s.icon className="h-5 w-5" />
              </div>
              <div>
                <div className="text-sm font-medium">{s.label}</div>
                <div className="text-xs text-muted-foreground">{s.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatsBody({
  query,
}: {
  query: {
    data:
      | (ReturnType<typeof statisticsService.get> extends Promise<infer T> ? T : never)
      | undefined;
    isLoading: boolean;
    isError: boolean;
    error: Error | null;
    refetch: () => void;
  };
}) {
  if (query.isLoading) return <LoadingState description="正在加载统计数据…" />;
  if (query.isError)
    return (
      <ErrorState
        description={query.error?.message ?? "加载失败"}
        onRetry={() => query.refetch()}
      />
    );
  if (!query.data) return <EmptyState title="暂无统计数据" />;

  const s = query.data;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="检查记录" total={s.records.inspection_records.total} />
        <StatCard label="拍照报告" total={s.records.photo_reports.total} />
        <StatCard label="询问笔录" total={s.records.interview_records.total} />
        <StatCard label="生成文书" total={s.generated_documents.total} />
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-muted-foreground">检查记录状态分布</span>
          <span className="font-medium">{s.records.inspection_records.total} 条</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(s.records.inspection_records.by_status).map(([k, v]) => (
            <span
              key={k}
              className="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs"
            >
              <RecordStatusBadge status={k} /> {v}
            </span>
          ))}
          {Object.keys(s.records.inspection_records.by_status).length === 0 && (
            <span className="text-xs text-muted-foreground">(暂无)</span>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, total }: { label: string; total: number }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{total}</div>
    </div>
  );
}

function TasksBody({
  query,
}: {
  query: {
    data: (ReturnType<typeof taskService.list> extends Promise<infer T> ? T : never) | undefined;
    isLoading: boolean;
    isError: boolean;
    error: Error | null;
    refetch: () => void;
  };
}) {
  if (query.isLoading) return <LoadingState description="正在加载任务…" />;
  if (query.isError)
    return (
      <ErrorState
        description={query.error?.message ?? "加载失败"}
        onRetry={() => query.refetch()}
      />
    );
  if (!query.data || query.data.items.length === 0)
    return <EmptyState title="暂无最近任务" description="提交生成任务后会显示在这里。" />;

  return (
    <div className="space-y-2">
      {query.data.items.map((t) => (
        <div
          key={t.task_id}
          className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-sm"
        >
          <div className="min-w-0">
            <div className="truncate font-medium">
              {TASK_TYPE_LABELS[t.task_type] ?? t.task_type}
            </div>
            <div className="text-xs text-muted-foreground">
              {TASK_STATUS_LABELS[t.status] ?? t.status}
              {t.status === "processing" && typeof t.progress === "number"
                ? " · " + t.progress + "%"
                : ""}
              {t.status === "failed" && t.error_message ? " · " + t.error_message.slice(0, 40) : ""}
            </div>
          </div>
          <span className="shrink-0 text-xs text-muted-foreground">
            {new Date(t.updated_at).toLocaleTimeString("zh-CN")}
          </span>
        </div>
      ))}
    </div>
  );
}

function KnowledgeBody({
  query,
}: {
  query: {
    data:
      | (ReturnType<typeof knowledgeService.status> extends Promise<infer T> ? T : never)
      | undefined;
    isLoading: boolean;
    isError: boolean;
    error: Error | null;
    refetch: () => void;
  };
}) {
  if (query.isLoading) return <LoadingState description="正在加载知识库状态…" />;
  if (query.isError)
    return (
      <ErrorState
        description={query.error?.message ?? "加载失败"}
        onRetry={() => query.refetch()}
      />
    );
  if (!query.data) return <EmptyState title="暂无知识库数据" />;

  const k = query.data;
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard label="文档总数" total={k.document_count} />
      <StatCard label="已索引" total={k.indexed_count} />
      <StatCard label="索引中" total={k.indexing_count} />
      <StatCard label="失败" total={k.failed_count} />
      <div className="col-span-2 text-xs text-muted-foreground">
        {k.last_indexed_at
          ? "最近索引:" + new Date(k.last_indexed_at).toLocaleString("zh-CN")
          : "尚未完成任何索引"}
      </div>
    </div>
  );
}
