import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { MODEL_KIND_LABELS, labelOf } from "@/lib/labels";
import {
  aiPlatformService,
  MODEL_KINDS,
  type ModelConfiguration,
  type ModelCreateBody,
  type ModelKind,
} from "@/lib/services/ai-platform";

export const Route = createFileRoute("/admin/models")({
  head: () => ({
    meta: [
      { title: "模型配置 · 消防智能助手" },
      { name: "description", content: "按能力类型管理模型配置:新建、编辑、优先级与启停。" },
    ],
  }),
  component: AdminModelsPage,
});

const ALL = "__all__";

function AdminModelsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [kindFilter, setKindFilter] = useState<ModelKind | undefined>(undefined);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ModelConfiguration | null>(null);
  const [deleting, setDeleting] = useState<ModelConfiguration | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin", "models"],
    queryFn: ({ signal }) => aiPlatformService.listModels(signal),
    enabled: isAdmin,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "models"] });

  const saveMutation = useMutation({
    mutationFn: (body: ModelCreateBody) =>
      editing
        ? aiPlatformService.updateModel(editing.id, body)
        : aiPlatformService.createModel(body),
    onSuccess: () => {
      toast.success(editing ? "模型配置已更新" : "模型配置已创建");
      setDialogOpen(false);
      setEditing(null);
      invalidate();
    },
    onError: (e) => toast.error(`保存失败:${readableAdminError(e, "请稍后重试")}`),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => aiPlatformService.deleteModel(id),
    onSuccess: () => {
      toast.success("模型配置已删除");
      setDeleting(null);
      invalidate();
    },
    onError: (e) => toast.error(`删除失败:${readableAdminError(e, "请稍后重试")}`),
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader title="模型配置" />
        <AdminAccessDenied />
      </div>
    );
  }

  const items = listQuery.data?.items ?? [];
  const filtered = (kindFilter ? items.filter((m) => m.kind === kindFilter) : items)
    .slice()
    .sort((a, b) => a.kind.localeCompare(b.kind) || a.priority - b.priority);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="模型配置"
        description="按能力类型配置模型路由;同类型下按优先级从高到低(数值小者优先)选用生效配置。"
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" /> 新建模型配置
          </Button>
        }
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">模型列表</CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={kindFilter ?? ALL}
              onValueChange={(v) => setKindFilter(v === ALL ? undefined : (v as ModelKind))}
            >
              <SelectTrigger className="h-8 w-36" aria-label="按能力类型过滤">
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>全部类型</SelectItem>
                {MODEL_KINDS.map((k) => (
                  <SelectItem key={k} value={k}>
                    {MODEL_KIND_LABELS[k]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
              description={readableAdminError(listQuery.error, "加载失败")}
              onRetry={() => listQuery.refetch()}
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="暂无模型配置"
              description={
                kindFilter
                  ? "当前类型下没有配置,可调整过滤条件。"
                  : "点击右上角「新建模型配置」创建第一条配置。"
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>提供商</TableHead>
                  <TableHead>模型</TableHead>
                  <TableHead>Base URL</TableHead>
                  <TableHead>密钥变量</TableHead>
                  <TableHead className="w-16">优先级</TableHead>
                  <TableHead className="w-20">状态</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">{m.name}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{labelOf(MODEL_KIND_LABELS, m.kind)}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{m.provider}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {m.model_name}
                    </TableCell>
                    <TableCell className="max-w-48 truncate font-mono text-xs text-muted-foreground">
                      {m.base_url ?? "—"}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {m.api_key_ref ?? "—"}
                    </TableCell>
                    <TableCell>{m.priority}</TableCell>
                    <TableCell>
                      <Badge variant={m.is_active ? "outline" : "destructive"}>
                        {m.is_active ? "生效" : "停用"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditing(m);
                            setDialogOpen(true);
                          }}
                          aria-label={`编辑 ${m.name}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => setDeleting(m)}
                          aria-label={`删除 ${m.name}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ModelFormDialog
        open={dialogOpen}
        editing={editing}
        isPending={saveMutation.isPending}
        error={saveMutation.error}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            setEditing(null);
            saveMutation.reset();
          }
        }}
        onSubmit={(body) => saveMutation.mutate(body)}
      />

      <AlertDialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除模型配置?</AlertDialogTitle>
            <AlertDialogDescription>
              将删除「{deleting?.name}」({deleting?.model_name}
              )。删除后该能力类型的模型路由将回退到其他生效配置或环境变量。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteMutation.error && (
            <p className="text-sm text-destructive">
              {readableAdminError(deleteMutation.error, "删除失败,请稍后重试")}
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>取消</AlertDialogCancel>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
            >
              {deleteMutation.isPending ? "删除中…" : "确认删除"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ModelFormDialog({
  open,
  editing,
  isPending,
  error,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  editing: ModelConfiguration | null;
  isPending: boolean;
  error: Error | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (body: ModelCreateBody) => void;
}) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ModelKind>("llm");
  const [provider, setProvider] = useState("");
  const [modelName, setModelName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKeyRef, setApiKeyRef] = useState("");
  const [priority, setPriority] = useState("0");
  const [isActive, setIsActive] = useState(true);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  // 打开对话框时按编辑对象初始化表单(渲染期派生,避免 effect 级联)。
  const formKey = open ? (editing?.id ?? "new") : null;
  if (formKey && formKey !== loadedFor) {
    setLoadedFor(formKey);
    setName(editing?.name ?? "");
    setKind(editing?.kind ?? "llm");
    setProvider(editing?.provider ?? "");
    setModelName(editing?.model_name ?? "");
    setBaseUrl(editing?.base_url ?? "");
    setApiKeyRef(editing?.api_key_ref ?? "");
    setPriority(String(editing?.priority ?? 0));
    setIsActive(editing?.is_active ?? true);
  }

  const priorityNum = Number.parseInt(priority, 10);
  const valid =
    name.trim().length > 0 &&
    provider.trim().length > 0 &&
    modelName.trim().length > 0 &&
    Number.isInteger(priorityNum);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing ? "编辑模型配置" : "新建模型配置"}</DialogTitle>
          <DialogDescription>
            模型路由优先使用生效配置,未命中时回退到环境变量配置。
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="model-name">名称</Label>
            <Input
              id="model-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如:主用 LLM"
            />
          </div>
          <div className="space-y-2">
            <Label>能力类型</Label>
            <Select value={kind} onValueChange={(v) => setKind(v as ModelKind)}>
              <SelectTrigger aria-label="能力类型">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MODEL_KINDS.map((k) => (
                  <SelectItem key={k} value={k}>
                    {MODEL_KIND_LABELS[k]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="model-provider">提供商</Label>
            <Input
              id="model-provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              placeholder="例如:openai"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="model-model-name">模型名</Label>
            <Input
              id="model-model-name"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="例如:gpt-4o"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="model-base-url">Base URL(可选)</Label>
            <Input
              id="model-base-url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="留空使用提供商默认地址"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="model-api-key-ref">密钥环境变量名(可选)</Label>
            <Input
              id="model-api-key-ref"
              value={apiKeyRef}
              onChange={(e) => setApiKeyRef(e.target.value)}
              placeholder="例如:OPENAI_API_KEY"
            />
            <p className="text-xs text-muted-foreground">
              仅填写环境变量名,不填写密钥本身;密钥只存放在服务端环境变量中。
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="model-priority">优先级(数值小者优先)</Label>
            <Input
              id="model-priority"
              type="number"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </div>
          <div className="flex items-end justify-between gap-4 pb-1">
            <div>
              <Label htmlFor="model-active">生效状态</Label>
              <p className="text-xs text-muted-foreground">停用后该配置不参与模型路由。</p>
            </div>
            <Switch id="model-active" checked={isActive} onCheckedChange={setIsActive} />
          </div>
        </div>
        {error && (
          <p className="text-sm text-destructive">
            {readableAdminError(error, "保存失败,请稍后重试")}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            取消
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                name: name.trim(),
                kind,
                provider: provider.trim(),
                model_name: modelName.trim(),
                base_url: baseUrl.trim() || undefined,
                api_key_ref: apiKeyRef.trim() || undefined,
                is_active: isActive,
                priority: priorityNum,
              })
            }
            disabled={!valid || isPending}
          >
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isPending ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
