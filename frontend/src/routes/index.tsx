import { createFileRoute, Link } from "@tanstack/react-router";
import {
  MessageSquareText,
  ClipboardList,
  Images,
  Mic,
  BookOpen,
  Settings as SettingsIcon,
} from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { UnavailableState } from "@/components/common/StateViews";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "工作台 · 消防智能助手" },
      { name: "description", content: "查看后端连接状态并快速进入各模块。" },
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

function Dashboard() {
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="工作台"
        description="查看系统状态,并快速进入各业务模块。统计数据将在后端接口就绪后加载。"
      />

      <div className="grid gap-4 md:grid-cols-2">
        <BackendStatusCard />
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">概览指标</CardTitle>
          </CardHeader>
          <CardContent>
            <UnavailableState
              title="统计数据暂未接入"
              description="GET /api/statistics 接口就绪后,此处将展示真实汇总数据。"
            />
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
                <div className="text-xs text-muted-foreground">进入模块</div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">最近任务</CardTitle>
          </CardHeader>
          <CardContent>
            <UnavailableState
              title="最近任务尚未提供"
              description="后端最近任务列表接口审批后,将在此显示您最近的生成任务与文档。"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
