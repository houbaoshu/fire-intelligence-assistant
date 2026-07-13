import { createFileRoute } from "@tanstack/react-router";
import { useState, type KeyboardEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Copy, Eraser, Loader2, Send } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/common/StateViews";
import { qaService, type QAAnswer } from "@/lib/services/qa";
import { toast } from "sonner";

export const Route = createFileRoute("/regulation-qa")({
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
    await navigator.clipboard.writeText(mutation.data.answer ?? "");
    toast.success("已复制答案");
  };

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
            placeholder="例如:高层民用建筑对疏散楼梯宽度有何要求?"
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

      <div className="mt-6">
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
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-sm">回答</CardTitle>
              <Button size="sm" variant="ghost" onClick={copy}>
                <Copy className="mr-2 h-4 w-4" /> 复制
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                {mutation.data.answer || "(未返回文本)"}
              </div>
              <div>
                <div className="mb-2 text-xs font-medium text-muted-foreground">来源</div>
                {mutation.data.sources && mutation.data.sources.length > 0 ? (
                  <ul className="space-y-2">
                    {mutation.data.sources.map((s, i) => (
                      <li
                        key={s.id ?? i}
                        className="rounded-md border border-border bg-muted/30 p-3 text-xs"
                      >
                        <div className="font-medium text-foreground">
                          {s.title ?? `来源 ${i + 1}`}
                        </div>
                        {s.snippet && (
                          <div className="mt-1 text-muted-foreground">{s.snippet}</div>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-xs text-muted-foreground">
                    本次回答未返回来源引用。
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {!mutation.isPending && !mutation.data && !mutation.error && (
          <EmptyState
            title="输入问题开始"
            description="所有回答均基于知识库检索,不做无依据的推理。"
          />
        )}
      </div>
    </div>
  );
}
