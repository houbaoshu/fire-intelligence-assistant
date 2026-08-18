import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Loader2, Play, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { AdminAccessDenied, ListPagination } from "@/components/admin/common";
import { readableAdminError } from "@/lib/admin-error";
import { useAuth } from "@/hooks/useAuth";
import { formatDateTime } from "@/lib/datetime";
import { EVALUATION_STATUS_LABELS, labelOf } from "@/lib/labels";
import {
  aiPlatformService,
  type EvaluationQuestion,
  type EvaluationRun,
  type EvaluationRunBody,
  type EvaluationRunDetail,
} from "@/lib/services/ai-platform";

export const Route = createFileRoute("/admin/evaluations")({
  head: () => ({
    meta: [
      { title: "评估运行 · 消防智能助手" },
      { name: "description", content: "运行检索问答评估并查看逐题结果。" },
    ],
  }),
  component: AdminEvaluationsPage,
});

const PAGE_SIZE = 20;

/** 表单中的问题行(关键词以逗号分隔文本维护,提交时拆分)。 */
type QuestionRow = {
  question: string;
  keywords: string;
  requireSource: boolean;
};

const emptyRow = (): QuestionRow => ({ question: "", keywords: "", requireSource: false });

function AdminEvaluationsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [detailId, setDetailId] = useState<string | null>(null);

  // ---- 运行表单状态 ----
  const [runName, setRunName] = useState("");
  const [rows, setRows] = useState<QuestionRow[]>([emptyRow()]);

  const listQuery = useQuery({
    queryKey: ["admin", "evaluations", page],
    queryFn: ({ signal }) =>
      aiPlatformService.listEvaluations({ page, page_size: PAGE_SIZE }, signal),
    enabled: isAdmin,
  });

  const detailQuery = useQuery({
    queryKey: ["admin", "evaluations", "detail", detailId],
    queryFn: ({ signal }) => aiPlatformService.getEvaluation(detailId as string, signal),
    enabled: isAdmin && detailId !== null,
  });

  const runMutation = useMutation({
    mutationFn: (body: EvaluationRunBody) => aiPlatformService.runEvaluation(body),
    onSuccess: () => {
      toast.success("评估已完成");
      setRunName("");
      setRows([emptyRow()]);
      setPage(1);
      qc.invalidateQueries({ queryKey: ["admin", "evaluations"] });
    },
    onError: (e) => toast.error(`评估失败:${readableAdminError(e, "请稍后重试")}`),
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader title="评估运行" />
        <AdminAccessDenied />
      </div>
    );
  }

  const updateRow = (index: number, patch: Partial<QuestionRow>) =>
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));

  const validQuestions: EvaluationQuestion[] = rows
    .filter((r) => r.question.trim().length > 0)
    .map((r) => {
      const keywords = r.keywords
        .split(/[,，]/)
        .map((k) => k.trim())
        .filter((k) => k.length > 0);
      return {
        question: r.question.trim(),
        expected_keywords: keywords.length > 0 ? keywords : undefined,
        require_source: r.requireSource || undefined,
      };
    });
  const canSubmit = runName.trim().length > 0 && validQuestions.length > 0;

  const data = listQuery.data;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="评估运行"
        description="对检索问答管线运行评估:真实调用 RAG 与模型,按关键词与来源要求计分。"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">运行新评估</CardTitle>
          <CardDescription>
            至少填写 1 个问题;关键词用逗号分隔,答案命中全部关键词且满足来源要求视为通过。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="eval-name">评估名称</Label>
            <Input
              id="eval-name"
              value={runName}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="例如:消防法规问答回归 2026-08"
              disabled={runMutation.isPending}
            />
          </div>
          <div className="space-y-3">
            <Label>问题列表</Label>
            {rows.map((row, index) => (
              <div
                key={index}
                className="flex flex-wrap items-start gap-3 rounded-md border border-border p-3"
              >
                <div className="min-w-56 flex-1 space-y-2">
                  <Input
                    value={row.question}
                    onChange={(e) => updateRow(index, { question: e.target.value })}
                    placeholder={`问题 ${index + 1}`}
                    aria-label={`问题 ${index + 1}`}
                    disabled={runMutation.isPending}
                  />
                  <Input
                    value={row.keywords}
                    onChange={(e) => updateRow(index, { keywords: e.target.value })}
                    placeholder="期望关键词,逗号分隔(可选)"
                    aria-label={`问题 ${index + 1} 期望关键词`}
                    disabled={runMutation.isPending}
                  />
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <Switch
                    id={`require-source-${index}`}
                    checked={row.requireSource}
                    onCheckedChange={(v) => updateRow(index, { requireSource: v })}
                    disabled={runMutation.isPending}
                  />
                  <Label htmlFor={`require-source-${index}`} className="text-xs">
                    要求引用来源
                  </Label>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setRows((prev) => prev.filter((_, i) => i !== index))}
                  disabled={rows.length <= 1 || runMutation.isPending}
                  aria-label={`删除问题 ${index + 1}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setRows((prev) => [...prev, emptyRow()])}
              disabled={runMutation.isPending}
            >
              <Plus className="mr-2 h-3.5 w-3.5" /> 添加问题
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={() =>
                runMutation.mutate({ name: runName.trim(), questions: validQuestions })
              }
              disabled={!canSubmit || runMutation.isPending}
            >
              {runMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {runMutation.isPending ? "评估运行中…" : "运行评估"}
            </Button>
            {runMutation.isPending && (
              <p className="text-xs text-muted-foreground">
                正在真实调用检索与模型管线,问题较多时可能需要几分钟,请勿关闭页面。
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">评估记录</CardTitle>
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
          ) : !data || data.items.length === 0 ? (
            <EmptyState title="暂无评估记录" description="在上方表单中运行第一次评估。" />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead className="w-24">状态</TableHead>
                    <TableHead className="w-28">通过率</TableHead>
                    <TableHead className="w-40">运行时间</TableHead>
                    <TableHead className="w-16" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="font-medium">{run.name}</TableCell>
                      <TableCell>
                        <Badge variant={run.status === "failed" ? "destructive" : "outline"}>
                          {labelOf(EVALUATION_STATUS_LABELS, run.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <PassRate run={run} />
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(run.created_at)}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => setDetailId(run.id)}
                          aria-label={`查看 ${run.name} 详情`}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <ListPagination
                page={data.page}
                total={data.total}
                pageSize={data.page_size}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={detailId !== null} onOpenChange={(open) => !open && setDetailId(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>评估详情</DialogTitle>
            <DialogDescription>{detailQuery.data?.name}</DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto">
            {detailQuery.isLoading ? (
              <LoadingState />
            ) : detailQuery.error ? (
              <ErrorState
                description={readableAdminError(detailQuery.error, "加载失败")}
                onRetry={() => detailQuery.refetch()}
              />
            ) : detailQuery.data ? (
              <EvaluationDetails details={detailQuery.data.details} />
            ) : null}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function PassRate({ run }: { run: EvaluationRun }) {
  const rate = run.total_questions > 0 ? Math.round((run.passed / run.total_questions) * 100) : 0;
  return (
    <span className="text-sm">
      <span className="font-medium">{rate}%</span>{" "}
      <span className="text-muted-foreground">
        ({run.passed}/{run.total_questions})
      </span>
    </span>
  );
}

/**
 * 逐题明细的容错渲染:details 内部结构由后端定义且可能演进,
 * 能识别出题目数组时结构化展示,否则原样展示 JSON。
 */
function EvaluationDetails({ details }: { details: unknown }) {
  const items = extractDetailItems(details);
  if (!items) {
    return (
      <pre className="whitespace-pre-wrap break-all rounded-md bg-muted p-3 font-mono text-xs">
        {JSON.stringify(details, null, 2)}
      </pre>
    );
  }
  if (items.length === 0) {
    return <EmptyState title="无逐题明细" />;
  }
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <DetailItem key={index} item={item} index={index} />
      ))}
    </div>
  );
}

function extractDetailItems(details: unknown): unknown[] | null {
  if (Array.isArray(details)) return details;
  if (details && typeof details === "object") {
    const record = details as Record<string, unknown>;
    for (const field of ["items", "results", "questions", "details"]) {
      const value = record[field];
      if (Array.isArray(value)) return value;
    }
  }
  return null;
}

function DetailItem({ item, index }: { item: unknown; index: number }) {
  if (!item || typeof item !== "object") {
    return (
      <pre className="whitespace-pre-wrap break-all rounded-md bg-muted p-3 font-mono text-xs">
        {JSON.stringify(item, null, 2)}
      </pre>
    );
  }
  const record = item as Record<string, unknown>;
  const question = typeof record.question === "string" ? record.question : null;
  const passed = typeof record.passed === "boolean" ? record.passed : null;
  const matched = Array.isArray(record.matched_keywords)
    ? record.matched_keywords.filter((k): k is string => typeof k === "string")
    : Array.isArray(record.hit_keywords)
      ? record.hit_keywords.filter((k): k is string => typeof k === "string")
      : null;
  const answer = typeof record.answer === "string" ? record.answer : null;

  // 字段全部不可识别时,整题回退为 JSON 展示。
  if (!question && passed === null && !answer) {
    return (
      <pre className="whitespace-pre-wrap break-all rounded-md bg-muted p-3 font-mono text-xs">
        {JSON.stringify(item, null, 2)}
      </pre>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-border p-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium">
          {index + 1}. {question ?? "(未提供问题文本)"}
        </p>
        {passed !== null && (
          <Badge variant={passed ? "outline" : "destructive"} className="shrink-0">
            {passed ? "通过" : "未通过"}
          </Badge>
        )}
      </div>
      {matched && matched.length > 0 && (
        <p className="text-xs text-muted-foreground">命中关键词:{matched.join("、")}</p>
      )}
      {answer && (
        <p className="line-clamp-3 whitespace-pre-wrap text-xs text-muted-foreground">{answer}</p>
      )}
    </div>
  );
}
