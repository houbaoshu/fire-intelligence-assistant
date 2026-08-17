import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowDown, ArrowLeft, ArrowUp, Loader2, Plus, Save, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { RecordStatusBadge } from "@/components/common/StatusBadges";
import { DocumentDownloadButton } from "@/components/common/DocumentDownloadButton";
import { RecordStatusActions } from "@/components/records/RecordStatusActions";
import { ApiError } from "@/lib/api-client";
import { useRecordEditor } from "@/hooks/useRecordEditor";
import {
  interviewRecordService,
  type InterviewRecordDetail,
  type InterviewRecordUpdate,
} from "@/lib/services/interview-record";
import { fromLocalInputValue, toLocalInputValue } from "@/lib/datetime";

export const Route = createFileRoute("/interview-record/$id")({
  head: () => ({
    meta: [
      { title: "询问笔录详情 · 消防智能助手" },
      {
        name: "description",
        content: "核对转写原文、编辑结构化询问记录,下载后端生成的 Word 文书。",
      },
    ],
  }),
  component: InterviewRecordDetailPage,
});

type QAForm = {
  /** 本地稳定 key,问答对无后端 id。 */
  localId: string;
  question: string;
  answer: string;
};

type FormState = {
  title: string;
  interviewee_name: string;
  interviewer_names: string;
  location: string;
  started_at: string;
  ended_at: string;
  transcript: string;
  /** structured_content 中除 questions_and_answers 外的其余键,保存时原样保留。 */
  structuredExtras: Record<string, unknown>;
  qas: QAForm[];
};

function toForm(detail: InterviewRecordDetail): FormState {
  const { questions_and_answers, ...extras } = detail.structured_content ?? {};
  return {
    title: detail.title ?? "",
    interviewee_name: detail.interviewee_name ?? "",
    interviewer_names: (detail.interviewer_names ?? []).join(", "),
    location: detail.location ?? "",
    started_at: toLocalInputValue(detail.started_at),
    ended_at: toLocalInputValue(detail.ended_at),
    transcript: detail.transcript ?? "",
    structuredExtras: extras,
    qas: (questions_and_answers ?? []).map((qa) => ({
      localId: crypto.randomUUID(),
      question: qa.question,
      answer: qa.answer,
    })),
  };
}

function buildPayload(form: FormState): InterviewRecordUpdate {
  return {
    title: form.title || null,
    interviewee_name: form.interviewee_name || null,
    interviewer_names: form.interviewer_names
      ? form.interviewer_names
          .split(/[,，、;；]+/)
          .map((s) => s.trim())
          .filter(Boolean)
      : null,
    location: form.location || null,
    started_at: form.started_at ? (fromLocalInputValue(form.started_at) ?? null) : null,
    ended_at: form.ended_at ? (fromLocalInputValue(form.ended_at) ?? null) : null,
    transcript: form.transcript || null,
    structured_content: {
      ...form.structuredExtras,
      questions_and_answers: form.qas.map(({ question, answer }) => ({ question, answer })),
    },
  };
}

function InterviewRecordDetailPage() {
  const { id } = Route.useParams();
  const { query, detail, form, dirty, update, discard, save, transition } = useRecordEditor({
    queryKey: ["interview-record", "detail", id],
    fetchDetail: (signal) => interviewRecordService.get(id, signal),
    toForm,
    buildPayload,
    updateRecord: (payload) => interviewRecordService.update(id, payload),
    setStatus: (status) => interviewRecordService.update(id, { status }),
  });

  if (query.isLoading || !form) {
    return (
      <div className="mx-auto max-w-4xl">
        <LoadingState title="加载笔录详情…" />
        {query.error && (
          <div className="mt-4">
            <ErrorState
              description={query.error instanceof Error ? query.error.message : "加载失败"}
              onRetry={() => query.refetch()}
            />
          </div>
        )}
      </div>
    );
  }

  if (query.error) {
    return (
      <div className="mx-auto max-w-4xl">
        <ErrorState
          title="笔录加载失败"
          description={query.error instanceof Error ? query.error.message : "加载失败"}
          onRetry={() => query.refetch()}
        />
      </div>
    );
  }

  const saveError = save.error;
  const isConflict = saveError instanceof ApiError && saveError.status === 409;

  const startIso = form.started_at ? fromLocalInputValue(form.started_at) : null;
  const endIso = form.ended_at ? fromLocalInputValue(form.ended_at) : null;
  const timeRangeInvalid = !!(startIso && endIso && startIso > endIso);

  const moveQA = (index: number, delta: number) =>
    update((f) => {
      const target = index + delta;
      if (target < 0 || target >= f.qas.length) return f;
      const qas = [...f.qas];
      [qas[index], qas[target]] = [qas[target], qas[index]];
      return { ...f, qas };
    });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            {detail?.title || "询问笔录"}
            {detail && <RecordStatusBadge status={detail.status} />}
          </span>
        }
        description="转写原文与结构化记录独立保存;请核对说话人、措辞与结构化内容后再定稿。"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/interview-record">
                <ArrowLeft className="mr-1 h-4 w-4" /> 返回列表
              </Link>
            </Button>
            {detail && (
              <DocumentDownloadButton
                fetchBlob={() => interviewRecordService.download(id)}
                filename={`interview-record-${detail.id}.docx`}
              />
            )}
          </div>
        }
      />

      {dirty && (
        <div className="flex items-center justify-between rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs text-amber-700 dark:text-amber-400">
          <span>有未保存的更改</span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              if (window.confirm("放弃未保存的更改?")) discard();
            }}
          >
            放弃更改
          </Button>
        </div>
      )}

      {saveError && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <div>保存失败:{saveError.message}</div>
          {isConflict && (
            <div className="mt-2 flex items-center gap-3 text-xs">
              <span>记录可能已被他人修改或已定稿,为避免覆盖请重新加载最新内容。</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  if (window.confirm("重新加载将放弃当前未保存的编辑,继续?")) {
                    discard();
                    void query.refetch();
                  }
                }}
              >
                放弃编辑并重新加载
              </Button>
            </div>
          )}
        </div>
      )}
      {transition.error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          状态变更失败:{transition.error.message}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">基本信息</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="title">标题</Label>
            <Input
              id="title"
              value={form.title}
              onChange={(e) => update((f) => ({ ...f, title: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="interviewee_name">被询问人</Label>
            <Input
              id="interviewee_name"
              value={form.interviewee_name}
              onChange={(e) => update((f) => ({ ...f, interviewee_name: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="interviewer_names">询问人(多人用逗号分隔)</Label>
            <Input
              id="interviewer_names"
              value={form.interviewer_names}
              onChange={(e) => update((f) => ({ ...f, interviewer_names: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="location">地点</Label>
            <Input
              id="location"
              value={form.location}
              onChange={(e) => update((f) => ({ ...f, location: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="started_at">开始时间</Label>
            <Input
              id="started_at"
              type="datetime-local"
              value={form.started_at}
              onChange={(e) => update((f) => ({ ...f, started_at: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ended_at">结束时间</Label>
            <Input
              id="ended_at"
              type="datetime-local"
              value={form.ended_at}
              onChange={(e) => update((f) => ({ ...f, ended_at: e.target.value }))}
            />
          </div>
          {timeRangeInvalid && (
            <div className="text-xs text-destructive md:col-span-2">
              开始时间不得晚于结束时间,请修正后再保存。
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">转写原文(Transcript)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">
            机器转写原文,人工校对后保存;听不清或不确定的片段请保留标注,不要凭推测补齐。
          </p>
          <Textarea
            rows={10}
            className="font-mono text-sm"
            value={form.transcript}
            onChange={(e) => update((f) => ({ ...f, transcript: e.target.value }))}
            placeholder="暂无转写内容"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm">
            结构化记录(问答 {form.qas.length} 条,与转写原文独立保存)
          </CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              update((f) => ({
                ...f,
                qas: [...f.qas, { localId: crypto.randomUUID(), question: "", answer: "" }],
              }))
            }
          >
            <Plus className="mr-1 h-4 w-4" /> 新增问答
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.qas.length === 0 && (
            <div className="text-sm text-muted-foreground">
              暂无结构化问答。结构化内容用于生成文书,不得用转写原文顶替。
            </div>
          )}
          {form.qas.map((qa, index) => (
            <div
              key={qa.localId}
              className="space-y-3 rounded-lg border border-border bg-card/50 p-4"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground">问答 {index + 1}</span>
                <div className="ml-auto flex items-center gap-1">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={() => moveQA(index, -1)}
                    disabled={index === 0}
                    aria-label="上移"
                  >
                    <ArrowUp className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={() => moveQA(index, 1)}
                    disabled={index === form.qas.length - 1}
                    aria-label="下移"
                  >
                    <ArrowDown className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive"
                    onClick={() =>
                      update((f) => {
                        const item = f.qas[index];
                        if (
                          (item.question || item.answer) &&
                          !window.confirm("该问答已有内容,确认删除?")
                        )
                          return f;
                        return { ...f, qas: f.qas.filter((_, i) => i !== index) };
                      })
                    }
                    aria-label="删除问答"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>问</Label>
                <Textarea
                  rows={2}
                  value={qa.question}
                  onChange={(e) =>
                    update((f) => ({
                      ...f,
                      qas: f.qas.map((it, i) =>
                        i === index ? { ...it, question: e.target.value } : it,
                      ),
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>答</Label>
                <Textarea
                  rows={3}
                  value={qa.answer}
                  onChange={(e) =>
                    update((f) => ({
                      ...f,
                      qas: f.qas.map((it, i) =>
                        i === index ? { ...it, answer: e.target.value } : it,
                      ),
                    }))
                  }
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {detail && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-4">
          <RecordStatusActions
            status={detail.status}
            dirty={dirty}
            pending={transition.isPending}
            onMarkReviewed={() => transition.mutate("reviewed")}
            onFinalize={() => {
              if (window.confirm("定稿后记录将进入已定稿状态,后续修改可能被拒绝(409)。确认定稿?"))
                transition.mutate("finalized");
            }}
          />
          <Button
            onClick={() => save.mutate()}
            disabled={!dirty || save.isPending || timeRangeInvalid}
          >
            {save.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            保存
          </Button>
        </div>
      )}
    </div>
  );
}
