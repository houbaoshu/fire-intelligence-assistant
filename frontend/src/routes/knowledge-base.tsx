import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Database,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { KnowledgeStatusBadge } from "@/components/common/StatusBadges";
import { useAuth } from "@/hooks/useAuth";
import { useResumableTask } from "@/hooks/useResumableTask";
import { ApiError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/datetime";
import { KNOWLEDGE_STATUS_LABELS } from "@/lib/labels";
import {
  KNOWLEDGE_DOCUMENT_STATUSES,
  knowledgeService,
  type KnowledgeDocument,
  type KnowledgeDocumentStatus,
} from "@/lib/services/knowledge";

export const Route = createFileRoute("/knowledge-base")({
  head: () => ({
    meta: [
      { title: "知识库 · 消防智能助手" },
      { name: "description", content: "管理供 RAG 使用的知识文档:上传、状态、删除与重建索引。" },
    ],
  }),
  component: KnowledgeBasePage,
});

/** 文档类上传白名单与上限(API.md §9);FileUpload 负责大小预校验,此处补充扩展名预校验。 */
const DOC_EXTENSIONS = [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"];
const DOC_MAX_SIZE = 50 * 1024 * 1024;
const ACCEPT = DOC_EXTENSIONS.join(",");
const PAGE_SIZE = 20;
const ALL = "__all__";

/** 统一可读错误;403 补充权限说明(后端校验为权威,前端仅 UX)。 */
function readableError(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return `没有权限执行此操作(${e.message})`;
    return e.message;
  }
  return e instanceof Error ? e.message : fallback;
}

function KnowledgeBasePage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  // 上传 / 删除 / 重建最低角色为 admin(specs/knowledge-base.md);非 admin 隐藏入口,仅 UX。
  const canManage = user?.role === "admin";

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<KnowledgeDocumentStatus | undefined>(undefined);
  const [file, setFile] = useState<File | null>(null);
  const [docToDelete, setDocToDelete] = useState<KnowledgeDocument | null>(null);
  const [rebuildOpen, setRebuildOpen] = useState(false);

  // 进行中的索引 / 重建任务持久化,页面刷新后可恢复进度展示(specs/_common.md)。
  const indexTask = useResumableTask("knowledge-indexing");
  const rebuildTask = useResumableTask("knowledge-rebuild");

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
    qc.invalidateQueries({ queryKey: ["knowledge-status"] });
  };

  const statusQuery = useQuery({
    queryKey: ["knowledge-status"],
    queryFn: ({ signal }) => knowledgeService.status(signal),
  });

  const listQuery = useQuery({
    queryKey: ["knowledge-documents", page, statusFilter],
    queryFn: ({ signal }) =>
      knowledgeService.list({ page, page_size: PAGE_SIZE, status: statusFilter }, signal),
  });

  const uploadMutation = useMutation({
    mutationFn: (f: File) => {
      const fd = new FormData();
      fd.append("file", f);
      return knowledgeService.upload(fd);
    },
    onSuccess: (res) => {
      toast.success("上传成功,后端已开始解析与索引");
      setFile(null);
      indexTask.setTaskId(res.task_id);
      invalidateAll();
    },
    onError: (e) => toast.error(`上传失败:${readableError(e, "请稍后重试")}`),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeService.remove(id),
    onSuccess: () => {
      toast.success("文档已删除");
      setDocToDelete(null);
      invalidateAll();
    },
    onError: (e) => toast.error(`删除失败:${readableError(e, "请稍后重试")}`),
  });

  const rebuildMutation = useMutation({
    mutationFn: () => knowledgeService.rebuild(),
    onSuccess: (res) => {
      toast.success("已触发全量索引重建");
      setRebuildOpen(false);
      rebuildTask.setTaskId(res.task_id);
    },
    onError: (e) => toast.error(`重建失败:${readableError(e, "请稍后重试")}`),
  });

  const submitUpload = () => {
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (!DOC_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
      toast.error(`不支持的文件类型,仅支持 ${DOC_EXTENSIONS.join(" / ")}`);
      return;
    }
    uploadMutation.mutate(file);
  };

  const data = listQuery.data;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="知识库"
        description="管理向 RAG 提供检索的源文档。上传后由后端解析、分块并建立向量索引。"
        actions={
          canManage ? (
            <Button variant="outline" onClick={() => setRebuildOpen(true)}>
              <Database className="mr-2 h-4 w-4" />
              重建索引
            </Button>
          ) : undefined
        }
      />

      <StatusSummary
        data={statusQuery.data}
        isLoading={statusQuery.isLoading}
        error={statusQuery.error}
        onRetry={() => statusQuery.refetch()}
      />

      {rebuildTask.taskId && (
        <TaskProgress
          taskId={rebuildTask.taskId}
          onComplete={() => {
            rebuildTask.setTaskId(null);
            invalidateAll();
          }}
          onFail={() => rebuildTask.setTaskId(null)}
        />
      )}

      {canManage && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">上传文档</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <FileUpload
              accept={ACCEPT}
              maxSize={DOC_MAX_SIZE}
              value={file}
              onChange={(v) => setFile(Array.isArray(v) ? (v[0] ?? null) : v)}
              hint="支持 pdf / doc / docx / ppt / pptx / txt / md,单文件不超过 50MB"
              disabled={uploadMutation.isPending}
            />
            <div className="flex justify-end">
              <Button onClick={submitUpload} disabled={!file || uploadMutation.isPending}>
                {uploadMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                {uploadMutation.isPending ? "上传中…" : "上传"}
              </Button>
            </div>
            {indexTask.taskId && (
              <div>
                <div className="mb-2 text-xs font-medium text-muted-foreground">
                  索引进度(与上传进度分开)
                </div>
                <TaskProgress
                  taskId={indexTask.taskId}
                  onComplete={() => {
                    indexTask.setTaskId(null);
                    toast.success("索引完成");
                    invalidateAll();
                  }}
                  onFail={() => {
                    indexTask.setTaskId(null);
                    invalidateAll();
                  }}
                />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">文档列表</CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={statusFilter ?? ALL}
              onValueChange={(v) => {
                setStatusFilter(v === ALL ? undefined : (v as KnowledgeDocumentStatus));
                setPage(1);
              }}
            >
              <SelectTrigger className="h-8 w-32" aria-label="按索引状态过滤">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>全部状态</SelectItem>
                {KNOWLEDGE_DOCUMENT_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {KNOWLEDGE_STATUS_LABELS[s]}
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
              description={readableError(listQuery.error, "加载失败")}
              onRetry={() => listQuery.refetch()}
            />
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              title="暂无文档"
              description={
                statusFilter
                  ? "当前过滤条件下没有文档,可切换状态过滤查看。"
                  : "上传第一个 PDF、Word、PPT 或文本文档以开始建立知识库。"
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标题</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>版本</TableHead>
                    <TableHead>发布机构</TableHead>
                    <TableHead>生效日期</TableHead>
                    <TableHead className="text-right">分块数</TableHead>
                    <TableHead>更新时间</TableHead>
                    {canManage && <TableHead className="w-12" />}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="max-w-56 truncate font-medium">{d.title}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {d.document_type ?? "—"}
                      </TableCell>
                      <TableCell>
                        <KnowledgeStatusBadge status={d.status} />
                      </TableCell>
                      <TableCell className="text-muted-foreground">{d.version ?? "—"}</TableCell>
                      <TableCell className="max-w-40 truncate text-muted-foreground">
                        {d.issuing_authority ?? "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {d.effective_date ?? "—"}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        {d.chunk_count ?? "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(d.updated_at)}
                      </TableCell>
                      {canManage && (
                        <TableCell>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setDocToDelete(d)}
                            aria-label={`删除 ${d.title}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  共 {data.total} 条 · 第 {data.page} / {totalPages} 页
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage(page - 1)}
                    disabled={page <= 1}
                  >
                    <ChevronLeft className="mr-1 h-3.5 w-3.5" /> 上一页
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage(page + 1)}
                    disabled={page >= totalPages}
                  >
                    下一页 <ChevronRight className="ml-1 h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={docToDelete !== null}
        onOpenChange={(open) => !open && setDocToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除文档?</AlertDialogTitle>
            <AlertDialogDescription>
              将删除「{docToDelete?.title}
              」并移除其全部索引数据,删除后该文档不再参与检索。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>取消</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleteMutation.isPending}
              onClick={(e) => {
                e.preventDefault();
                if (docToDelete) deleteMutation.mutate(docToDelete.id);
              }}
            >
              {deleteMutation.isPending ? "删除中…" : "确认删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={rebuildOpen} onOpenChange={setRebuildOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认重建全部索引?</AlertDialogTitle>
            <AlertDialogDescription>
              将对全部知识库文档重建向量索引,代价较高且重建期间检索结果可能暂时不完整。同一时刻只允许一个重建任务。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={rebuildMutation.isPending}>取消</AlertDialogCancel>
            <AlertDialogAction
              disabled={rebuildMutation.isPending}
              onClick={(e) => {
                e.preventDefault();
                rebuildMutation.mutate();
              }}
            >
              {rebuildMutation.isPending ? "提交中…" : "确认重建"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function StatusSummary({
  data,
  isLoading,
  error,
  onRetry,
}: {
  data:
    | {
        document_count: number;
        indexed_count: number;
        indexing_count: number;
        failed_count: number;
        last_indexed_at: string | null;
      }
    | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  if (isLoading) return <LoadingState title="加载知识库状态…" />;
  if (error || !data) {
    return (
      <ErrorState
        title="知识库状态加载失败"
        description={readableError(error, "加载失败")}
        onRetry={onRetry}
      />
    );
  }
  const items = [
    { label: "文档总数", value: data.document_count },
    { label: "已索引", value: data.indexed_count },
    { label: "索引中", value: data.indexing_count },
    { label: "失败", value: data.failed_count, danger: data.failed_count > 0 },
  ];
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-3 p-4">
        {items.map((it) => (
          <div key={it.label}>
            <div className="text-xs text-muted-foreground">{it.label}</div>
            <div
              className={`text-xl font-semibold ${it.danger ? "text-destructive" : "text-foreground"}`}
            >
              {it.value}
            </div>
          </div>
        ))}
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          {data.failed_count > 0 && <AlertTriangle className="h-3.5 w-3.5 text-destructive" />}
          最近索引时间:{formatDateTime(data.last_indexed_at)}
        </div>
      </CardContent>
    </Card>
  );
}
