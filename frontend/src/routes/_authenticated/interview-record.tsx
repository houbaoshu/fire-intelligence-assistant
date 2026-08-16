import { createFileRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  FileCheck2,
  Loader2,
  Mic,
  Plus,
  RefreshCw,
  Save,
  Upload,
} from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { RecordStatusBadge } from "@/components/common/RecordStatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import {
  interviewRecordService,
  type InterviewRecord,
  type InterviewUpdate,
} from "@/lib/services/interview-record";
import { RECORD_STATUS_LABELS } from "@/lib/record-status";
import { ApiError } from "@/lib/api-client";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/interview-record")({
  head: () => ({
    meta: [
      { title: "询问笔录 · 消防智能助手" },
      { name: "description", content: "上传询问录音,生成结构化询问笔录草稿。" },
    ],
  }),
  component: InterviewRecordPage,
});

const STATUS_FILTERS = [
  "draft",
  "processing",
  "generated",
  "reviewed",
  "finalized",
  "archived",
  "failed",
];

function InterviewRecordPage() {
  const routerState = useRouterState();
  const search = routerState.location.search as Record<string, unknown>;
  const selectedId = typeof search.id === "string" ? search.id : null;
  const newMode = typeof search.action === "string" && search.action === "new";

  if (selectedId) return <DetailView id={selectedId} />;
  if (newMode) return <NewView />;
  return <ListView />;
}

function ListView() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const query = useQuery({
    queryKey: ["interview-records", { status }],
    queryFn: ({ signal }) =>
      interviewRecordService.list({ page: 1, page_size: 50, status: status || undefined }, signal),
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="询问笔录"
        description="上传询问录音,后端将识别语音并生成结构化笔录草稿。"
        actions={
          <Button onClick={() => navigate({ to: "/interview-record", search: { action: "new" } })}>
            <Plus className="mr-2 h-4 w-4" /> 新建询问记录
          </Button>
        }
      />
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">记录列表</CardTitle>
          <div className="flex items-center gap-2">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-md border border-input bg-background px-2 py-1 text-sm"
            >
              <option value="">全部状态</option>
              {STATUS_FILTERS.map((s) => (
                <option key={s} value={s}>
                  {RECORD_STATUS_LABELS[s] ?? s}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")}
              />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {query.isLoading ? (
            <LoadingState description="正在加载记录…" />
          ) : query.isError ? (
            <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
          ) : query.data && query.data.items.length === 0 ? (
            <EmptyState
              title="还没有询问记录"
              description="点击右上角「新建询问记录」上传录音开始生成。"
            />
          ) : (
            <div className="divide-y">
              {query.data?.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate({ to: "/interview-record", search: { id: item.id } })}
                  className="flex w-full items-center justify-between gap-3 py-3 text-left transition hover:bg-accent/40"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">
                        {item.title || item.interviewee_name || "未命名记录"}
                      </span>
                      <RecordStatusBadge status={item.status} />
                    </div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {item.interviewee_name ? "被询问人:" + item.interviewee_name + " · " : ""}
                      {new Date(item.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                  <Mic className="h-4 w-4 shrink-0 text-muted-foreground" />
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function NewView() {
  const navigate = useNavigate();
  const [audio, setAudio] = useState<File | null>(null);
  const [remarks, setRemarks] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);

  const generateMutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (audio) fd.append("audio", audio);
      if (remarks.trim()) fd.append("remarks", remarks.trim());
      return interviewRecordService.generate(fd);
    },
    onSuccess: (res) => {
      setTaskId(res.task_id);
      toast.success("已提交生成任务");
    },
    onError: (e) => toast.error("提交失败:" + e.message),
  });

  const onTaskComplete = useCallback(
    (task: { result_data: Record<string, unknown> | null }) => {
      const recordId = task.result_data?.record_id;
      toast.success("询问记录生成完成");
      if (typeof recordId === "string") {
        navigate({ to: "/interview-record", search: { id: recordId } });
      }
    },
    [navigate],
  );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="新建询问记录"
        description="上传一段询问录音(wav / mp3 / m4a,≤200MB),后端异步转写并生成结构化笔录。"
        actions={
          <Button variant="outline" onClick={() => navigate({ to: "/interview-record" })}>
            <ArrowLeft className="mr-2 h-4 w-4" /> 返回列表
          </Button>
        }
      />
      {!taskId && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">上传录音</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FileUpload
              accept="audio/wav,audio/mpeg,audio/mp4,.wav,.mp3,.m4a"
              value={audio}
              onChange={(v) => setAudio(Array.isArray(v) ? (v[0] ?? null) : v)}
              hint="wav / mp3 / m4a,单个文件,≤200MB"
              disabled={generateMutation.isPending}
            />
            <div className="space-y-2">
              <Label htmlFor="remarks">备注(可选)</Label>
              <Textarea
                id="remarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={3}
                placeholder="填写询问人、地点等补充信息"
                disabled={generateMutation.isPending}
              />
            </div>
            <div className="flex justify-end">
              <Button
                onClick={() => generateMutation.mutate()}
                disabled={!audio || generateMutation.isPending}
              >
                {generateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                提交生成
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      {taskId && (
        <TaskProgress
          taskId={taskId}
          onComplete={onTaskComplete}
          onFail={() => toast.error("生成失败,请查看任务详情")}
        />
      )}
    </div>
  );
}

function DetailView({ id }: { id: string }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [record, setRecord] = useState<InterviewRecord | null>(null);
  const [dirty, setDirty] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["interview-record", id],
    queryFn: ({ signal }) => interviewRecordService.get(id, signal),
    enabled: !!id,
  });

  useEffect(() => {
    if (detailQuery.data) {
      setRecord(detailQuery.data);
      setDirty(false);
    }
  }, [detailQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (patch: InterviewUpdate) => interviewRecordService.update(id, patch),
    onSuccess: (updated) => {
      setRecord(updated);
      setDirty(false);
      toast.success("已保存");
      qc.invalidateQueries({ queryKey: ["interview-records"] });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) {
        toast.error("记录已定稿,不能直接修改");
      } else {
        toast.error("保存失败:" + e.message);
      }
    },
  });

  const onTaskComplete = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["interview-record", id] });
    detailQuery.refetch();
    toast.success("文书生成完成");
  }, [qc, id, detailQuery]);

  const patchRecord = (patch: Partial<InterviewRecord>) => {
    setRecord((prev) => (prev ? { ...prev, ...patch } : prev));
    setDirty(true);
  };

  const patchQA = (index: number, patch: Record<string, string>) => {
    setRecord((prev) => {
      if (!prev) return prev;
      const qa = [...(prev.structured_content?.questions_and_answers ?? [])];
      if (!qa[index]) return prev;
      qa[index] = { ...qa[index], ...patch };
      return {
        ...prev,
        structured_content: { ...(prev.structured_content ?? {}), questions_and_answers: qa },
      };
    });
    setDirty(true);
  };

  const removeQA = (index: number) => {
    setRecord((prev) => {
      if (!prev) return prev;
      const qa = (prev.structured_content?.questions_and_answers ?? []).filter(
        (_, i) => i !== index,
      );
      return {
        ...prev,
        structured_content: { ...(prev.structured_content ?? {}), questions_and_answers: qa },
      };
    });
    setDirty(true);
  };

  const addQA = () => {
    setRecord((prev) => {
      if (!prev) return prev;
      const qa = [
        ...(prev.structured_content?.questions_and_answers ?? []),
        { question: "", answer: "" },
      ];
      return {
        ...prev,
        structured_content: { ...(prev.structured_content ?? {}), questions_and_answers: qa },
      };
    });
    setDirty(true);
  };

  const download = async () => {
    const tok = localStorage.getItem("fip.auth.access_token");
    try {
      const res = await fetch(interviewRecordService.downloadUrl(id), {
        headers: tok ? { Authorization: "Bearer " + tok } : {},
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        toast.error((body && body.error && body.error.message) || "文书尚未生成");
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "interview-record-" + id + ".docx";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      toast.error("下载失败:" + (e as Error).message);
    }
  };

  const isFinalized = record?.status === "finalized";
  const isProcessing = record?.status === "processing";
  const canEdit = !isFinalized && !isProcessing;
  const activeTaskId = isProcessing ? record?.source_task_id : null;
  const qa = record?.structured_content?.questions_and_answers ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="询问笔录"
        description={record?.title || "加载中…"}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate({ to: "/interview-record" })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> 返回列表
            </Button>
            {record?.status === "finalized" && (
              <Button onClick={download}>
                <Download className="mr-2 h-4 w-4" /> 下载文书
              </Button>
            )}
          </>
        }
      />
      {detailQuery.isLoading && <LoadingState description="正在加载记录详情…" />}
      {detailQuery.isError && !record && (
        <ErrorState description={detailQuery.error.message} onRetry={() => detailQuery.refetch()} />
      )}
      {activeTaskId && (
        <TaskProgress
          taskId={activeTaskId}
          onComplete={onTaskComplete}
          onFail={() => toast.error("生成失败,请查看任务详情")}
        />
      )}
      {record && (
        <>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-sm">记录信息</CardTitle>
              <RecordStatusBadge status={record.status} />
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Field label="标题">
                <Input
                  value={record.title ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ title: e.target.value })}
                />
              </Field>
              <Field label="被询问人">
                <Input
                  value={record.interviewee_name ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ interviewee_name: e.target.value })}
                />
              </Field>
              <Field label="询问人(顿号分隔)">
                <Input
                  value={(record.interviewer_names ?? []).join("、")}
                  disabled={!canEdit}
                  onChange={(e) =>
                    patchRecord({
                      interviewer_names: e.target.value
                        .split(/[,，、]/)
                        .map((s) => s.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </Field>
              <Field label="地点">
                <Input
                  value={record.location ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ location: e.target.value })}
                />
              </Field>
              <Field label="开始时间">
                <Input
                  type="datetime-local"
                  value={record.started_at ? record.started_at.slice(0, 16) : ""}
                  disabled={!canEdit}
                  onChange={(e) =>
                    patchRecord({
                      started_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                    })
                  }
                />
              </Field>
              <Field label="结束时间">
                <Input
                  type="datetime-local"
                  value={record.ended_at ? record.ended_at.slice(0, 16) : ""}
                  disabled={!canEdit}
                  onChange={(e) =>
                    patchRecord({
                      ended_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                    })
                  }
                />
              </Field>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">转写原文(Transcript)</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                rows={10}
                value={record.transcript ?? ""}
                disabled={!canEdit}
                onChange={(e) => patchRecord({ transcript: e.target.value })}
                className="font-mono text-xs"
              />
              <p className="mt-2 text-xs text-muted-foreground">
                转写原文与结构化内容分开保存;原始机器转写在校订后仍保留可查。
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-sm">结构化内容(问答)</CardTitle>
              {canEdit && (
                <Button size="sm" variant="outline" onClick={addQA}>
                  <Plus className="mr-2 h-3.5 w-3.5" /> 添加问答
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {qa.length === 0 && (
                <EmptyState title="暂无问答内容" description="AI 整理或手动添加问答。" />
              )}
              {qa.map((item, idx) => (
                <div key={idx} className="rounded-lg border border-border p-3">
                  <div className="space-y-2">
                    <Field label={"问题 " + (idx + 1)}>
                      <Textarea
                        rows={2}
                        value={item.question}
                        disabled={!canEdit}
                        onChange={(e) => patchQA(idx, { question: e.target.value })}
                      />
                    </Field>
                    <Field label="回答">
                      <Textarea
                        rows={3}
                        value={item.answer}
                        disabled={!canEdit}
                        onChange={(e) => patchQA(idx, { answer: e.target.value })}
                      />
                    </Field>
                  </div>
                  {canEdit && (
                    <div className="mt-2 flex justify-end">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => removeQA(idx)}
                      >
                        删除
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-center justify-end gap-2">
            {dirty && <span className="text-xs text-muted-foreground">有未保存的更改</span>}
            {canEdit && (
              <Button
                onClick={() => saveMutation.mutate(collectPatch(record))}
                disabled={!dirty || saveMutation.isPending}
              >
                {saveMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                保存
              </Button>
            )}
            {canEdit && record.transcript && qa.length > 0 && (
              <Button
                onClick={() => saveMutation.mutate({ status: "finalized" })}
                disabled={saveMutation.isPending}
              >
                <FileCheck2 className="mr-2 h-4 w-4" /> 定稿并生成文书
              </Button>
            )}
            {record.status === "finalized" && (
              <Button onClick={download}>
                <Download className="mr-2 h-4 w-4" /> 下载文书
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function collectPatch(record: InterviewRecord): InterviewUpdate {
  return {
    title: record.title ?? undefined,
    interviewee_name: record.interviewee_name ?? undefined,
    interviewer_names: record.interviewer_names ?? undefined,
    location: record.location ?? undefined,
    started_at: record.started_at ?? undefined,
    ended_at: record.ended_at ?? undefined,
    transcript: record.transcript ?? undefined,
    structured_content: record.structured_content ?? undefined,
  };
}

function Field({ label, children, full }: { label: string; children: ReactNode; full?: boolean }) {
  return (
    <div className={full ? "md:col-span-2 space-y-1.5" : "space-y-1.5"}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
