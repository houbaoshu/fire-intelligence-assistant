import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  ClipboardList,
  Images,
  MessageSquareText,
  Mic,
  Settings as SettingsIcon,
} from "lucide-react";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { PageHeader } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { statisticsService } from "@/lib/services/statistics";
import { taskService } from "@/lib/services/tasks";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "工作台 · 消防智能助手" }] }),
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

function Dashboard() {
  const statistics = useQuery({
    queryKey: ["statistics"],
    queryFn: ({ signal }) => statisticsService.get(signal),
  });
  const tasks = useQuery({
    queryKey: ["tasks", "recent"],
    queryFn: ({ signal }) => taskService.list(signal),
  });

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="工作台" description="真实系统状态、当前账号可见的业务汇总和最近任务。" />
      <BackendStatusCard />

      <section className="mt-6" aria-labelledby="metrics-title">
        <h2 id="metrics-title" className="mb-3 text-sm font-medium text-muted-foreground">
          业务概览
        </h2>
        {statistics.isLoading ? (
          <LoadingState title="正在加载统计" />
        ) : statistics.error ? (
          <ErrorState description={statistics.error.message} onRetry={() => statistics.refetch()} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {statistics.data?.metrics.map((metric) => (
              <Card key={metric.id}>
                <CardContent className="p-4">
                  <div className="text-xs text-muted-foreground">{metric.label}</div>
                  <div className="mt-1 text-2xl font-semibold">
                    {metric.available && metric.value !== null ? metric.value : "不可用"}
                    {metric.available && metric.value !== null && (
                      <span className="ml-1 text-xs font-normal">{metric.unit}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="mt-6" aria-labelledby="shortcuts-title">
        <h2 id="shortcuts-title" className="mb-3 text-sm font-medium text-muted-foreground">
          快捷入口
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SHORTCUTS.map((shortcut) => (
            <Link
              key={shortcut.to}
              to={shortcut.to}
              className="flex items-center gap-3 rounded-lg border bg-card p-4 hover:bg-accent/40"
            >
              <shortcut.icon className="h-5 w-5 text-primary" />
              <span className="text-sm font-medium">{shortcut.label}</span>
            </Link>
          ))}
        </div>
      </section>

      <Card className="mt-6">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">最近任务</CardTitle>
          <Link to="/tasks" className="text-xs text-primary hover:underline">
            查看全部
          </Link>
        </CardHeader>
        <CardContent>
          {tasks.isLoading ? (
            <LoadingState />
          ) : tasks.error ? (
            <ErrorState description={tasks.error.message} onRetry={() => tasks.refetch()} />
          ) : !tasks.data?.items.length ? (
            <EmptyState title="暂无任务" description="提交生成或索引后，任务会显示在这里。" />
          ) : (
            <ul className="space-y-2">
              {tasks.data.items.slice(0, 5).map((task) => (
                <li
                  key={task.id}
                  className="flex items-center justify-between rounded-md border p-3 text-sm"
                >
                  <span>{task.task_type}</span>
                  <Badge variant="outline">{task.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
