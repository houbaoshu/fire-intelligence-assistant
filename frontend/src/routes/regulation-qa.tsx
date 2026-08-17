import { createFileRoute } from "@tanstack/react-router";
import { useState, type KeyboardEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, Copy, Eraser, Loader2, RotateCcw, Send } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/common/StateViews";
import { SourceCitationList } from "@/components/qa/SourceCitations";
import { formatSourcesForCopy } from "@/components/qa/sourceText";
import { ApiError } from "@/lib/api-client";
import { qaService, type QAResponse } from "@/lib/services/qa";

export const Route = createFileRoute("/regulation-qa")({
  head: () => ({
    meta: [
      { title: "法规问答 · 消防智能助手" },
      { name: "description", content: "基于知识库检索并生成的消防法规问答,附来源引用。" },
    ],
  }),
  component: RegulationQA,
});

/** 问题长度上限(specs/regulation-qa.md:4,000 字符,前后端均校验)。 */
const MAX_LEN = 4000;

function readableError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return `没有权限执行此操作(${e.message})`;
    return e.message;
  }
  return e instanceof Error ? e.message : "请求失败,请稍后重试";
}

function RegulationQA() {
  const [question, setQuestion] = useState("");
  const mutation = useMutation<QAResponse, Error, string>({
    mutationFn: (q) => qaService.query(q),
  });

  const trimmed = question.trim();
  const canSubmit = trimmed.length > 0 && !mutation.isPending;

  const submit = () => {
    if (!canSubmit) return;
    mutation.mutate(trimmed);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter 提交,Shift+Enter 换行(specs/regulation-qa.md)。
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const clear = () => {
    setQuestion("");
    mutation.reset();
  };

  const copy = async () => {
    if (!mutation.data) return;
    const { answer, sources } = mutation.data;
    const text =
      sources.length > 0
        ? `${answer}\n\n来源:\n${formatSourcesForCopy(sources)}`
        : `${answer}\n\n来源:未检索到可靠来源`;
    try {
      await navigator.clipboard.writeText(text);
      toast.success("已复制回答与来源清单");
    } catch {
      toast.error("复制失败,请手动选择文本复制");
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="法规问答"
        description="用中文提出消防法规问题。回答基于知识库检索结果生成并附来源引用;AI 输出仅为辅助意见,不能替代法律审查或官方法律决定。"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">提问</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value.slice(0, MAX_LEN))}
            onKeyDown={onKeyDown}
            placeholder="例如:高层民用建筑对疏散楼梯宽度有何要求?"
            rows={4}
            aria-label="法规问题"
          />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Enter 发送 · Shift+Enter 换行</span>
            <span>
              {question.length} / {MAX_LEN}
            </span>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={clear} disabled={mutation.isPending}>
              <Eraser className="mr-2 h-4 w-4" /> 清空
            </Button>
            <Button onClick={submit} disabled={!canSubmit}>
              {mutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              提问
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 回答更新与错误需对辅助技术可感知(specs/regulation-qa.md)。 */}
      <div aria-live="polite">
        {mutation.isPending && (
          <Card>
            <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> 正在检索知识库并生成回答…
            </CardContent>
          </Card>
        )}

        {mutation.error && (
          <ErrorState
            title="问答请求失败"
            description={`${readableError(mutation.error)}。问题文本已保留,可重试。`}
            action={
              <Button
                size="sm"
                variant="outline"
                onClick={() => mutation.mutate(trimmed)}
                disabled={!trimmed || mutation.isPending}
              >
                <RotateCcw className="mr-2 h-3.5 w-3.5" /> 重试
              </Button>
            }
          />
        )}

        {mutation.data && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
              <CardTitle className="text-sm">回答</CardTitle>
              <Button size="sm" variant="ghost" onClick={copy}>
                <Copy className="mr-2 h-4 w-4" /> 复制
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {mutation.data.sources.length === 0 && (
                <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  未检索到可靠来源。以下内容为模型在证据不足情况下的说明,不构成法律结论,请以官方发布文本为准。
                </div>
              )}
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                {mutation.data.answer}
              </div>
              <p className="text-xs text-muted-foreground">
                以上回答由 AI
                基于知识库检索生成,仅为辅助意见,不能替代检查人员的法律审查或官方法律决定。
              </p>
              <div>
                <div className="mb-2 text-xs font-medium text-muted-foreground">
                  来源({mutation.data.sources.length})
                </div>
                {mutation.data.sources.length > 0 ? (
                  <SourceCitationList sources={mutation.data.sources} />
                ) : (
                  <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
                    本次回答未检索到可靠来源,未引用任何法规文档。
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {!mutation.isPending && !mutation.data && !mutation.error && (
          <EmptyState
            title="输入问题开始"
            description="所有回答均基于知识库中已索引的法规文档检索生成,并附可追溯的来源引用,不做无依据的推理。"
          />
        )}
      </div>
    </div>
  );
}
