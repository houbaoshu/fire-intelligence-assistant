import { createFileRoute } from "@tanstack/react-router";
import { useState, type KeyboardEvent, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { Copy, Eraser, Loader2, Send, BookOpen } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/common/StateViews";
import { qaService, type QAAnswer } from "@/lib/services/qa";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/regulation-qa")({
  head: () => ({
    meta: [
      { title: "法规问答 · 消防智能助手" },
      { name: "description", content: "基于知识库检索并生成的消防法规问答,附来源引用。" },
    ],
  }),
  component: RegulationQA,
});

const MAX_LEN = 4000;

function RegulationQA() {
  const [question, setQuestion] = useState("");
  const mutation = useMutation<QAAnswer, Error, string>({
    mutationFn: (q) => qaService.ask(q),
  });

  const trimmed = question.trim();
  const canSubmit = trimmed.length > 0 && !mutation.isPending;

  const submit = () => {
    if (!canSubmit) return;
    mutation.mutate(trimmed);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const copy = async () => {
    if (!mutation.data) return;
    const sourcesText = (mutation.data.sources ?? [])
      .map(
        (s, i) =>
          i +
          1 +
          ". " +
          s.title +
          (s.article ? " · " + s.article : "") +
          (s.effective_date ? " · " + s.effective_date : ""),
      )
      .join("\n");
    await navigator.clipboard.writeText(
      mutation.data.answer + (sourcesText ? "\n\n来源:\n" + sourcesText : ""),
    );
    toast.success("已复制答案与来源");
  };

  const noEvidence = mutation.data && mutation.data.sources.length === 0;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="法规问答"
        description="用中文提出消防法规问题,回答将基于知识库检索结果生成并附来源引用。"
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
            placeholder="例如:消防安全出口被锁闭时适用哪些规定?"
            rows={4}
          />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Enter 发送 · Shift+Enter 换行</span>
            <span>
              {question.length} / {MAX_LEN}
            </span>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setQuestion("");
                mutation.reset();
              }}
            >
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

      <div className="mt-6 space-y-4">
        {mutation.isPending && (
          <Card>
            <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> 检索并生成中…
            </CardContent>
          </Card>
        )}

        {mutation.error && (
          <ErrorState
            description={mutation.error.message}
            onRetry={() => mutation.mutate(trimmed)}
          />
        )}

        {mutation.data && (
          <>
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="text-sm">回答</CardTitle>
                <Button size="sm" variant="ghost" onClick={copy}>
                  <Copy className="mr-2 h-4 w-4" /> 复制
                </Button>
              </CardHeader>
              <CardContent>
                {noEvidence ? (
                  <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-700">
                    知识库中未检索到足够的相关材料,以下为证据不足说明,不构成法律意见:
                  </div>
                ) : null}
                <div className="whitespace-pre-wrap text-sm leading-7">{mutation.data.answer}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center gap-2">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-sm">来源引用 ({mutation.data.sources.length})</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {mutation.data.sources.length === 0 ? (
                  <EmptyState
                    title="未返回来源"
                    description="本次回答未基于知识库检索结果,请补充相关法规文档后再试。"
                  />
                ) : (
                  mutation.data.sources.map((s, i) => (
                    <div key={i} className="rounded-md border border-border p-3">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium">{s.title}</span>
                        {s.article && (
                          <span className="text-xs text-muted-foreground">{s.article}</span>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {[
                          s.issuing_authority,
                          s.version,
                          s.effective_date ? "生效 " + s.effective_date : null,
                          s.page !== null && s.page !== undefined ? "第 " + s.page + " 页" : null,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </div>
                      {s.excerpt && (
                        <div className="mt-2 rounded bg-muted/60 p-2 text-xs leading-5 text-muted-foreground">
                          {s.excerpt}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </>
        )}

        {!mutation.data && !mutation.isPending && !mutation.error && (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              <div className="mb-2 font-medium">使用说明</div>
              <ul className="list-disc space-y-1 pl-5 text-xs">
                <li>回答基于知识库中已索引的法规文档生成,禁止编造法规依据。</li>
                <li>每条回答附带可追溯的来源引用(文档、条款、页码与摘录)。</li>
                <li>证据不足时会明确提示,不会给出无依据的法律结论。</li>
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
