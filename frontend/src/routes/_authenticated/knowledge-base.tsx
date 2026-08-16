import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import {
  knowledgeService,
  KNOWLEDGE_STATUS_LABELS,
  type KnowledgeDocument,
  type KnowledgeStatus,
} from "@/lib/services/knowledge";
import { Loader2, RefreshCw, Trash2, Upload, Database } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export const Route = createFileRoute("/_authenticated/knowledge-base")({
  head: () => ({
    meta: [
      { title: "知识库 · 消防智能助手" },
      { name: "description", content: "管理供 RAG 使用的知识文档:上传、状态、删除与重建索引。" },
    ],
  }),
  component: KnowledgeBasePage,
});

const STATUS_TONES: Record<string, string> = {
  uploaded: "bg-muted text-muted-foreground",
  parsing: "bg-blue-500/15 text-blue-600",
  indexing: "bg-blue-500/15 text-blue-600",
  indexed: "bg-emerald-500/15 text-emerald-700",
  failed: "bg-destructive/15 text-destructive",
  outdated: "bg-amber-500/15 text-amber-700",
};

function KnowledgeBasePage() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [indexingTaskId, setIndexingTaskId] = useState<string | null>(null);
  const [rebuildTaskId, setRebuildTaskId] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["knowledge-documents", { status: statusFilter }],
    queryFn: ({ signal }) =>
      knowledgeService.list({ page: 1, page_size: 50, status: statusFilter || undefined }, signal),
  });

  const statusQuery = useQuery({
    queryKey: ["knowledge-status"],
    queryFn: ({ signal }) => knowledgeService.status(signal),
  });

  const uploadMutation = useMutation({
    mutationFn: (f: File) => knowledgeService.upload(f),
    onSuccess: (res) => {
      toast.success("已提交上传与索引任务");
      setFile(null);
      setIndexingTaskId(res.task_id);
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
      qc.invalidateQueries({ queryKey: ["knowledge-status"] });
    },
    onError: (e: Error) => toast.error("上传失败:" + e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeService.delete(id),
    onSuccess: () => {
      toast.success("已删除文档并移除索引");
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
      qc.invalidateQueries({ queryKey: ["knowledge-status"] });
    },
    onError: (e: Error) => toast.error("删除失败:" + e.message),
  });

  const rebuildMutation = useMutation({
    mutationFn: () => knowledgeService.rebuild(),
    onSuccess: (res) => {
      toast.success("已触发索引重建");
      setRebuildTaskId(res.task_id);
    },
    onError: (e: Error) => toast.error("重建失败:" + e.message),
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="知识库"
        description="管理向 RAG 提供检索的源文档。上传后由后端进行解析、切分与向量索引。"
        actions={
          <Button
            variant="outline"
            onClick={() => rebuildMutation.mutate()}
            disabled={rebuildMutation.isPending || rebuildTaskId !== null}
          >
            <Database className="mr-2 h-4 w-4" />
            重建索引
          </Button>
        }
      />

      {rebuildTaskId && (
        <div className="mb-4">
          <TaskProgress
            taskId={rebuildTaskId}
            onComplete={() => {
              qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
              qc.invalidateQueries({ queryKey: ["knowledge-status"] });
              toast.success("索引重建完成");
            }}
          />
        </div>
      )}

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        <CountCard label="文档总数" value={statusQuery.data?.document_count} />
        <CountCard label="已索引" value={statusQuery.data?.indexed_count} />
        <CountCard label="索引中" value={statusQuery.data?.indexing_count} />
        <CountCard label="失败" value={statusQuery.data?.failed_count} />
      </div>

      {indexingTaskId && (
        <div className="mb-4">
          <TaskProgress
            taskId={indexingTaskId}
            onComplete={() => {
              setIndexingTaskId(null);
              qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
              qc.invalidateQueries({ queryKey: ["knowledge-status"] });
              toast.success("文档索引完成");
            }}
            onFail={() => {
              setIndexingTaskId(null);
              qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
              toast.error("文档索引失败");
            }}
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">上传文档</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FileUpload
            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md"
            value={file}
            onChange={(v) => setFile(Array.isArray(v) ? (v[0] ?? null) : v)}
            hint="支持 pdf / doc / docx / ppt / pptx / txt / md,≤50MB"
            disabled={uploadMutation.isPending}
          />
          <div className="flex justify-end">
            <Button
              onClick={() => file && uploadMutation.mutate(file)}
              disabled={!file || uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              上传
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="mt-6">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-sm">文档列表</CardTitle>
            <div className="flex items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-md border border-input bg-background px-2 py-1 text-sm"
              >
                <option value="">全部状态</option>
                {Object.entries(KNOWLEDGE_STATUS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => listQuery.refetch()}
                disabled={listQuery.isFetching}
              >
                <RefreshCw
                  className={"mr-2 h-3.5 w-3.5 " + (listQuery.isFetching ? "animate-spin" : "")}
                />
                刷新
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {listQuery.isLoading ? (
              <LoadingState description="正在加载文档…" />
            ) : listQuery.isError ? (
              <ErrorState
                description={listQuery.error.message}
                onRetry={() => listQuery.refetch()}
              />
            ) : listQuery.data && listQuery.data.items.length === 0 ? (
              <EmptyState
                title="知识库为空"
                description="上传法规文档后,系统将自动解析、切分并建立向量索引。"
              />
            ) : (
              <div className="divide-y">
                {listQuery.data?.items.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    doc={doc}
                    onDelete={(id) => deleteMutation.mutate(id)}
                    deleting={deleteMutation.isPending}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CountCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value === undefined ? "…" : value}</div>
    </div>
  );
}

function DocumentRow({
  doc,
  onDelete,
  deleting,
}: {
  doc: KnowledgeDocument;
  onDelete: (id: string) => void;
  deleting: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate text-sm font-medium">{doc.title}</span>
          <span
            className={
              "rounded-full px-2 py-0.5 text-xs " +
              (STATUS_TONES[doc.status] ?? "bg-muted text-muted-foreground")
            }
          >
            {KNOWLEDGE_STATUS_LABELS[doc.status] ?? doc.status}
          </span>
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {[
            doc.document_type,
            doc.issuing_authority,
            doc.version ? "版本 " + doc.version : null,
            doc.effective_date ? "生效 " + doc.effective_date : null,
            doc.chunk_count !== null && doc.chunk_count !== undefined
              ? doc.chunk_count + " chunks"
              : null,
            new Date(doc.updated_at).toLocaleString("zh-CN"),
          ]
            .filter(Boolean)
            .join(" · ")}
        </div>
        {doc.status === "failed" && (
          <div className="mt-1 text-xs text-destructive">索引导入失败,可删除后重新上传。</div>
        )}
      </div>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            size="sm"
            variant="ghost"
            className="shrink-0 text-destructive"
            disabled={deleting}
          >
            <Trash2 className="mr-2 h-3.5 w-3.5" /> 删除
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除知识文档</AlertDialogTitle>
            <AlertDialogDescription>
              确定删除「{doc.title}」吗?将同时移除其向量索引数据,删除后不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => onDelete(doc.id)}>确认删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
