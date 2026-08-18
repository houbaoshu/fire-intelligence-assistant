import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Loader2, Pencil, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
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
import { AdminAccessDenied } from "@/components/admin/common";
import { readableAdminError } from "@/lib/admin-error";
import { useAuth } from "@/hooks/useAuth";
import { formatDateTime } from "@/lib/datetime";
import {
  aiPlatformService,
  type PromptVersion,
  type PromptVersionCreateBody,
} from "@/lib/services/ai-platform";

export const Route = createFileRoute("/admin/prompts")({
  head: () => ({
    meta: [
      { title: "Prompt 管理 · 消防智能助手" },
      { name: "description", content: "管理平台 Prompt:版本历史、创建新版本与激活。" },
    ],
  }),
  component: AdminPromptsPage,
});

/** 按 key 分组的 Prompt:版本按版本号降序。 */
type PromptGroup = {
  key: string;
  versions: PromptVersion[];
  active: PromptVersion | null;
  latest: PromptVersion;
};

function AdminPromptsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<PromptGroup | null>(null);
  const [activating, setActivating] = useState<PromptVersion | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin", "prompts"],
    queryFn: ({ signal }) => aiPlatformService.listPrompts(signal),
    enabled: isAdmin,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "prompts"] });

  const createMutation = useMutation({
    mutationFn: ({ key, body }: { key: string; body: PromptVersionCreateBody }) =>
      aiPlatformService.createPromptVersion(key, body),
    onSuccess: () => {
      toast.success("新版本已创建,激活后生效");
      setEditing(null);
      invalidate();
    },
    onError: (e) => toast.error(`创建失败:${readableAdminError(e, "请稍后重试")}`),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => aiPlatformService.activatePrompt(id),
    onSuccess: () => {
      toast.success("已激活该版本");
      setActivating(null);
      invalidate();
    },
    onError: (e) => toast.error(`激活失败:${readableAdminError(e, "请稍后重试")}`),
  });

  const groups = useMemo<PromptGroup[]>(() => {
    const items = listQuery.data?.items ?? [];
    const byKey = new Map<string, PromptVersion[]>();
    for (const v of items) {
      const list = byKey.get(v.key);
      if (list) list.push(v);
      else byKey.set(v.key, [v]);
    }
    return [...byKey.entries()]
      .map(([key, versions]) => {
        versions.sort((a, b) => b.version - a.version);
        const latest = versions[0];
        return { key, versions, latest, active: versions.find((v) => v.is_active) ?? null };
      })
      .sort((a, b) => a.key.localeCompare(b.key));
  }, [listQuery.data]);

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-5xl">
        <PageHeader title="Prompt 管理" />
        <AdminAccessDenied />
      </div>
    );
  }

  const toggleExpanded = (key: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="Prompt 管理"
        description="查看各 Prompt 的版本历史,创建新版本并激活。仅生效版本参与线上生成。"
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">Prompt 列表</CardTitle>
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
        <CardContent className="space-y-3">
          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.error ? (
            <ErrorState
              description={readableAdminError(listQuery.error, "加载失败")}
              onRetry={() => listQuery.refetch()}
            />
          ) : groups.length === 0 ? (
            <EmptyState title="暂无 Prompt" description="后端尚未登记任何 Prompt 版本。" />
          ) : (
            groups.map((group) => {
              const expanded = expandedKeys.has(group.key);
              return (
                <div key={group.key} className="rounded-md border border-border">
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/50"
                    onClick={() => toggleExpanded(group.key)}
                    aria-expanded={expanded}
                  >
                    {expanded ? (
                      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{group.latest.name ?? group.key}</span>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {group.key}
                        </Badge>
                        {group.active ? (
                          <Badge variant="outline">生效中 v{group.active.version}</Badge>
                        ) : (
                          <Badge variant="destructive">无生效版本</Badge>
                        )}
                      </div>
                      {group.latest.description && (
                        <p className="mt-1 truncate text-xs text-muted-foreground">
                          {group.latest.description}
                        </p>
                      )}
                    </div>
                  </button>
                  {expanded && (
                    <div className="border-t border-border p-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <span className="text-xs text-muted-foreground">
                          共 {group.versions.length} 个版本
                        </span>
                        <Button size="sm" variant="outline" onClick={() => setEditing(group)}>
                          <Pencil className="mr-2 h-3.5 w-3.5" /> 创建新版本
                        </Button>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-20">版本</TableHead>
                            <TableHead className="w-24">状态</TableHead>
                            <TableHead className="w-40">创建时间</TableHead>
                            <TableHead>内容预览</TableHead>
                            <TableHead className="w-24" />
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {group.versions.map((v) => (
                            <TableRow key={v.id}>
                              <TableCell className="font-mono">v{v.version}</TableCell>
                              <TableCell>
                                {v.is_active ? (
                                  <Badge>生效中</Badge>
                                ) : (
                                  <Badge variant="secondary">历史</Badge>
                                )}
                              </TableCell>
                              <TableCell className="text-muted-foreground">
                                {formatDateTime(v.created_at)}
                              </TableCell>
                              <TableCell className="max-w-80 truncate font-mono text-xs text-muted-foreground">
                                {v.content.slice(0, 120)}
                              </TableCell>
                              <TableCell>
                                {!v.is_active && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setActivating(v)}
                                  >
                                    激活
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </CardContent>
      </Card>

      <PromptEditDialog
        group={editing}
        isPending={createMutation.isPending}
        error={createMutation.error}
        onOpenChange={(open) => {
          if (!open) {
            setEditing(null);
            createMutation.reset();
          }
        }}
        onSubmit={(body) => editing && createMutation.mutate({ key: editing.key, body })}
      />

      <AlertDialog open={activating !== null} onOpenChange={(open) => !open && setActivating(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认激活该版本?</AlertDialogTitle>
            <AlertDialogDescription>
              将把「{activating?.key}」的 v{activating?.version}{" "}
              设为生效版本,原生效版本同时失效。线上生成将立即使用新内容。
            </AlertDialogDescription>
          </AlertDialogHeader>
          {activateMutation.error && (
            <p className="text-sm text-destructive">
              {readableAdminError(activateMutation.error, "激活失败,请稍后重试")}
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={activateMutation.isPending}>取消</AlertDialogCancel>
            <Button
              disabled={activateMutation.isPending}
              onClick={() => activating && activateMutation.mutate(activating.id)}
            >
              {activateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {activateMutation.isPending ? "激活中…" : "确认激活"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/** 创建新版本对话框:以当前生效(或最新)版本内容为基础编辑。 */
function PromptEditDialog({
  group,
  isPending,
  error,
  onOpenChange,
  onSubmit,
}: {
  group: PromptGroup | null;
  isPending: boolean;
  error: Error | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (body: PromptVersionCreateBody) => void;
}) {
  const [content, setContent] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  // 打开对话框时以生效版本(无生效则用最新版本)初始化表单(渲染期派生,避免 effect 级联)。
  if (group && group.key !== loadedFor) {
    setLoadedFor(group.key);
    const baseVersion = group.active ?? group.latest;
    setContent(baseVersion.content);
    setName(baseVersion.name ?? "");
    setDescription(baseVersion.description ?? "");
  }

  const baseVersion = group ? (group.active ?? group.latest) : null;

  return (
    <Dialog open={group !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>创建新版本</DialogTitle>
          <DialogDescription>
            {group?.key} · 当前基于 v{baseVersion?.version}{" "}
            编辑;保存后生成新版本,需手动激活才会生效。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prompt-content">Prompt 内容</Label>
            <Textarea
              id="prompt-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={14}
              className="font-mono text-xs"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="prompt-name">名称(可选)</Label>
              <Input id="prompt-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="prompt-description">描述(可选)</Label>
              <Input
                id="prompt-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>
        </div>
        {error && (
          <p className="text-sm text-destructive">
            {readableAdminError(error, "创建失败,请稍后重试")}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            取消
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                content,
                name: name.trim() || undefined,
                description: description.trim() || undefined,
              })
            }
            disabled={content.trim().length === 0 || isPending}
          >
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isPending ? "保存中…" : "保存为新版本"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
