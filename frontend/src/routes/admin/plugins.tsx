import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { AdminAccessDenied } from "@/components/admin/common";
import { readableAdminError } from "@/lib/admin-error";
import { useAuth } from "@/hooks/useAuth";
import { aiPlatformService, type AdminPlugin } from "@/lib/services/ai-platform";

export const Route = createFileRoute("/admin/plugins")({
  head: () => ({
    meta: [
      { title: "插件管理 · 消防智能助手" },
      { name: "description", content: "查看服务端插件注册表并切换启用状态。" },
    ],
  }),
  component: AdminPluginsPage,
});

function AdminPluginsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["admin", "plugins"],
    queryFn: ({ signal }) => aiPlatformService.listPlugins(signal),
    enabled: isAdmin,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      aiPlatformService.updatePlugin(id, enabled),
    // 乐观更新开关;失败时回滚缓存并展示后端可读错误。
    onMutate: async ({ id, enabled }) => {
      await qc.cancelQueries({ queryKey: ["admin", "plugins"] });
      const previous = qc.getQueryData<{ items: AdminPlugin[] }>(["admin", "plugins"]);
      if (previous) {
        qc.setQueryData<{ items: AdminPlugin[] }>(["admin", "plugins"], {
          items: previous.items.map((p) => (p.id === id ? { ...p, enabled } : p)),
        });
      }
      return { previous };
    },
    onError: (e, _vars, context) => {
      if (context?.previous) qc.setQueryData(["admin", "plugins"], context.previous);
      toast.error(`切换失败:${readableAdminError(e, "请稍后重试")}`);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["admin", "plugins"] }),
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-5xl">
        <PageHeader title="插件管理" />
        <AdminAccessDenied />
      </div>
    );
  }

  const items = listQuery.data?.items ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="插件管理"
        description="服务端插件注册表;切换启用状态立即生效,禁用后插件钩子不再执行。"
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">插件列表</CardTitle>
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
        </CardHeader>
        <CardContent>
          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.error ? (
            <ErrorState
              description={readableAdminError(listQuery.error, "加载失败")}
              onRetry={() => listQuery.refetch()}
            />
          ) : items.length === 0 ? (
            <EmptyState title="暂无插件" description="后端尚未注册任何插件。" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead className="w-20">版本</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>入口</TableHead>
                  <TableHead className="w-20">启用</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell>
                      {p.version ? <Badge variant="secondary">v{p.version}</Badge> : "—"}
                    </TableCell>
                    <TableCell className="max-w-72 truncate text-muted-foreground">
                      {p.description ?? "—"}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {p.entry_point}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={p.enabled}
                        onCheckedChange={(enabled) => toggleMutation.mutate({ id: p.id, enabled })}
                        aria-label={`切换 ${p.name} 启用状态`}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
