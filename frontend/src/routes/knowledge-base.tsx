import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileUpload } from "@/components/common/FileUpload";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/common/StateViews";
import { knowledgeService, type KnowledgeDocument } from "@/lib/services/knowledge";
import { Loader2, RefreshCw, Trash2, Upload, Database } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/knowledge-base")({
  head: () => ({
    meta: [
      { title: "知识库 · 消防智能助手" },
      { name: "description", content: "管理供 RAG 使用的知识文档:上传、状态、删除与重建索引。" },
    ],
  }),
  component: KnowledgeBasePage,
});

function KnowledgeBasePage() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);

  const listQuery = useQuery({
    queryKey: ["knowledge-documents"],
    queryFn: ({ signal }) => knowledgeService.list(signal),
  });

  const uploadMutation = useMutation({
    mutationFn: (f: File) => knowledgeService.upload(f),
    onSuccess: () => {
      toast.success("已提交上传");
      setFile(null);
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
    },
    onError: (e: Error) => toast.error(`上传失败:${e.message}`),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeService.delete(id),
    onSuccess: () => {
      toast.success("已删除");
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
    },
    onError: (e: Error) => toast.error(`删除失败:${e.message}`),
  });

  const rebuildMutation = useMutation({
    mutationFn: () => knowledgeService.rebuild(),
    onSuccess: () => toast.success("已触发索引重建"),
    onError: (e: Error) => toast.error(`重建失败:${e.message}`),
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="知识库"
        description="管理向 RAG 提供检索的源文档。上传后由后端进行解析与索引。"
        actions={
          <Button
            variant="outline"
            onClick={() => rebuildMutation.mutate()}
            disabled={rebuildMutation.isPending}
          >
            <Database className="mr-2 h-4 w-4" />
            重建索引
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">上传文档</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FileUpload
            accept=".pdf,.doc,.docx,.ppt,.pptx"
            value={file}
            onChange={(v) => setFile(Array.isArray(v) ? v[0] ?? null : v)}
            hint="支持 pdf / doc / docx / ppt / pptx"
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
                description={(listQuery.error as Error).message}
                onRetry={() => listQuery.refetch()}
              />
            ) : !listQuery.data || listQuery.data.length === 0 ? (
              <EmptyState
                title="暂无文档"
                description="上传第一个 PDF、Word 或 PPT 文档以开始建立知识库。"
              />
            ) : (
              <ul className="space-y-2">
                {listQuery.data.map((d) => (
                  <DocRow key={d.id} doc={d} onDelete={() => deleteMutation.mutate(d.id)} />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DocRow({ doc, onDelete }: { doc: KnowledgeDocument; onDelete: () => void }) {
  return (
    <li className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{doc.name}</div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
          {doc.status && <Badge variant="outline">{doc.status}</Badge>}
          {doc.updated_at && <span>更新于 {doc.updated_at}</span>}
        </div>
        {doc.error && <div className="mt-1 text-xs text-destructive">{doc.error}</div>}
      </div>
      <Button size="icon" variant="ghost" onClick={onDelete} aria-label="删除">
        <Trash2 className="h-4 w-4" />
      </Button>
    </li>
  );
}
