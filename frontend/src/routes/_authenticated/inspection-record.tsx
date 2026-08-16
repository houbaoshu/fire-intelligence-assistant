import { createFileRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ClipboardList,
  Download,
  FileCheck2,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { RecordStatusBadge } from "@/components/common/RecordStatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import {
  inspectionRecordService,
  type InspectionRecord,
  type InspectionUpdate,
} from "@/lib/services/inspection-record";
import { ITEM_TYPE_LABELS, RECORD_STATUS_LABELS, SEVERITY_LABELS } from "@/lib/record-status";
import { ApiError } from "@/lib/api-client";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/inspection-record")({
  head: () => ({
    meta: [
      { title: "检查记录 · 消防智能助手" },
      { name: "description", content: "上传检查视频,生成结构化检查记录草稿并导出 Word。" },
    ],
  }),
  component: InspectionRecordPage,
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

function InspectionRecordPage() {
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
    queryKey: ["inspection-records", { status }],
    queryFn: ({ signal }) =>
      inspectionRecordService.list({ page: 1, page_size: 50, status: status || undefined }, signal),
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="检查记录"
        description="上传现场检查视频,生成结构化检查记录草稿,审阅后导出 Word 文书。"
        actions={
          <Button onClick={() => navigate({ to: "/inspection-record", search: { action: "new" } })}>
            <Plus className="mr-2 h-4 w-4" /> 新建检查记录
          </Button>
        }
      />
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">记录列表</CardTitle>
          <div className="flex items-center gap-2">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">全部状态</SelectItem>
                {STATUS_FILTERS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {RECORD_STATUS_LABELS[s] ?? s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
            <LoadingState description="正在加载检查记录…" />
          ) : query.isError ? (
            <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
          ) : query.data && query.data.items.length === 0 ? (
            <EmptyState
              title="还没有检查记录"
              description="点击右上角「新建检查记录」上传现场视频开始生成。"
            />
          ) : (
            <div className="divide-y">
              {query.data?.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate({ to: "/inspection-record", search: { id: item.id } })}
                  className="flex w-full items-center justify-between gap-3 py-3 text-left transition hover:bg-accent/40"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">
                        {item.title || item.inspection_unit || "未命名记录"}
                      </span>
                      <RecordStatusBadge status={item.status} />
                    </div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {item.record_number ? item.record_number + " · " : ""}
                      {item.inspection_unit ? item.inspection_unit + " · " : ""}
                      {new Date(item.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                  <ClipboardList className="h-4 w-4 shrink-0 text-muted-foreground" />
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
  const [file, setFile] = useState<File | null>(null);
  const [remarks, setRemarks] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);

  const generateMutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (file) fd.append("video", file);
      if (remarks.trim()) fd.append("remarks", remarks.trim());
      return inspectionRecordService.generate(fd);
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
      toast.success("检查记录生成完成");
      if (typeof recordId === "string") {
        navigate({ to: "/inspection-record", search: { id: recordId } });
      }
    },
    [navigate],
  );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="新建检查记录"
        description="上传一段现场检查视频与可选备注,提交后由后端异步生成结构化草稿。"
        actions={
          <Button variant="outline" onClick={() => navigate({ to: "/inspection-record" })}>
            <ArrowLeft className="mr-2 h-4 w-4" /> 返回列表
          </Button>
        }
      />
      {!taskId && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">上传视频</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FileUpload
              accept="video/mp4,video/quicktime,.mp4,.mov"
              value={file}
              onChange={(v) => setFile(Array.isArray(v) ? (v[0] ?? null) : v)}
              hint="仅支持 mp4 / mov,单个文件,≤500MB"
              disabled={generateMutation.isPending}
            />
            <div className="space-y-2">
              <Label htmlFor="remarks">备注(可选)</Label>
              <Textarea
                id="remarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={3}
                placeholder="填写检查地点、现场情况等补充信息"
                disabled={generateMutation.isPending}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => generateMutation.mutate()}
                disabled={!file || generateMutation.isPending}
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
  const [record, setRecord] = useState<InspectionRecord | null>(null);
  const [dirty, setDirty] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["inspection-record", id],
    queryFn: ({ signal }) => inspectionRecordService.get(id, signal),
    enabled: !!id,
  });

  useEffect(() => {
    if (detailQuery.data) {
      setRecord(detailQuery.data);
      setDirty(false);
    }
  }, [detailQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (patch: InspectionUpdate) => inspectionRecordService.update(id, patch),
    onSuccess: (updated) => {
      setRecord(updated);
      setDirty(false);
      toast.success("已保存");
      qc.invalidateQueries({ queryKey: ["inspection-records"] });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) {
        toast.error("记录已定稿,不能直接修改;如需修订请走重新生成流程");
      } else {
        toast.error("保存失败:" + e.message);
      }
    },
  });

  const onTaskComplete = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["inspection-record", id] });
    detailQuery.refetch();
    toast.success("文书生成完成");
  }, [qc, id, detailQuery]);

  const patchRecord = (patch: Partial<InspectionRecord>) => {
    setRecord((prev) => (prev ? { ...prev, ...patch } : prev));
    setDirty(true);
  };

  const patchItem = (index: number, patch: Record<string, unknown>) => {
    setRecord((prev) => {
      if (!prev) return prev;
      const items = prev.items.map((it, i) => (i === index ? { ...it, ...patch } : it));
      return { ...prev, items };
    });
    setDirty(true);
  };

  const removeItem = (index: number) => {
    setRecord((prev) => {
      if (!prev) return prev;
      return { ...prev, items: prev.items.filter((_, i) => i !== index) };
    });
    setDirty(true);
  };

  const addItem = () => {
    setRecord((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: [
          ...prev.items,
          {
            id: "new-" + Date.now(),
            item_type: "observation" as const,
            location: null,
            description: "",
            legal_basis: null,
            correction_requirement: null,
            severity: null,
            sort_order: prev.items.length,
          },
        ],
      };
    });
    setDirty(true);
  };

  const download = async () => {
    const tok = localStorage.getItem("fip.auth.access_token");
    try {
      const res = await fetch(inspectionRecordService.downloadUrl(id), {
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
      a.download = "inspection-record-" + (record?.record_number || id) + ".docx";
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

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="检查记录"
        description={record ? (record.record_number || "") + " " + (record.title || "") : "加载中…"}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate({ to: "/inspection-record" })}>
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
              <Field label="记录编号">
                <Input value={record.record_number ?? ""} disabled />
              </Field>
              <Field label="标题">
                <Input
                  value={record.title ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ title: e.target.value })}
                />
              </Field>
              <Field label="被检查单位">
                <Input
                  value={record.inspection_unit ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ inspection_unit: e.target.value })}
                />
              </Field>
              <Field label="检查地址">
                <Input
                  value={record.inspection_address ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ inspection_address: e.target.value })}
                />
              </Field>
              <Field label="检查日期">
                <Input
                  type="date"
                  value={record.inspection_date ? record.inspection_date.slice(0, 10) : ""}
                  disabled={!canEdit}
                  onChange={(e) =>
                    patchRecord({
                      inspection_date: e.target.value
                        ? new Date(e.target.value).toISOString()
                        : null,
                    })
                  }
                />
              </Field>
              <Field label="检查人员(顿号分隔)">
                <Input
                  value={(record.inspector_names ?? []).join("、")}
                  disabled={!canEdit}
                  onChange={(e) =>
                    patchRecord({
                      inspector_names: e.target.value
                        .split(/[,，、]/)
                        .map((s) => s.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </Field>
              <Field label="联系人">
                <Input
                  value={record.contact_person ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ contact_person: e.target.value })}
                />
              </Field>
              <Field label="联系电话">
                <Input
                  value={record.contact_phone ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ contact_phone: e.target.value })}
                />
              </Field>
              <Field label="检查情况概述" full>
                <Textarea
                  rows={3}
                  value={record.summary ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ summary: e.target.value })}
                />
              </Field>
              <Field label="检查结论" full>
                <Textarea
                  rows={3}
                  value={record.conclusion ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchRecord({ conclusion: e.target.value })}
                />
              </Field>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-sm">检查发现项</CardTitle>
              {canEdit && (
                <Button size="sm" variant="outline" onClick={addItem}>
                  <Plus className="mr-2 h-3.5 w-3.5" /> 添加检查项
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {record.items.length === 0 && (
                <EmptyState title="暂无检查项" description="AI 生成或手动添加检查发现项。" />
              )}
              {record.items.map((item, idx) => (
                <div key={item.id} className="rounded-lg border border-border p-3">
                  <div className="grid gap-3 md:grid-cols-3">
                    <Field label="类型">
                      <Select
                        value={item.item_type}
                        disabled={!canEdit}
                        onValueChange={(v) => patchItem(idx, { item_type: v })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(ITEM_TYPE_LABELS).map(([k, v]) => (
                            <SelectItem key={k} value={k}>
                              {v}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="位置">
                      <Input
                        value={item.location ?? ""}
                        disabled={!canEdit}
                        onChange={(e) => patchItem(idx, { location: e.target.value })}
                      />
                    </Field>
                    <Field label="严重程度">
                      <Select
                        value={item.severity ?? "medium"}
                        disabled={!canEdit}
                        onValueChange={(v) => patchItem(idx, { severity: v })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(SEVERITY_LABELS).map(([k, v]) => (
                            <SelectItem key={k} value={k}>
                              {v}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                  </div>
                  <div className="mt-3">
                    <Field label="问题描述">
                      <Textarea
                        rows={2}
                        value={item.description}
                        disabled={!canEdit}
                        onChange={(e) => patchItem(idx, { description: e.target.value })}
                      />
                    </Field>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <Field label="法律依据">
                      <Textarea
                        rows={2}
                        value={item.legal_basis ?? ""}
                        disabled={!canEdit}
                        onChange={(e) => patchItem(idx, { legal_basis: e.target.value })}
                      />
                    </Field>
                    <Field label="整改要求">
                      <Textarea
                        rows={2}
                        value={item.correction_requirement ?? ""}
                        disabled={!canEdit}
                        onChange={(e) => patchItem(idx, { correction_requirement: e.target.value })}
                      />
                    </Field>
                  </div>
                  {canEdit && (
                    <div className="mt-3 flex justify-end">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => removeItem(idx)}
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" /> 删除
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
            {canEdit && record.items.length > 0 && (
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

function collectPatch(record: InspectionRecord): InspectionUpdate {
  return {
    title: record.title ?? undefined,
    inspection_unit: record.inspection_unit ?? undefined,
    inspection_address: record.inspection_address ?? undefined,
    inspection_date: record.inspection_date ?? undefined,
    inspector_names: record.inspector_names ?? undefined,
    contact_person: record.contact_person ?? undefined,
    contact_phone: record.contact_phone ?? undefined,
    summary: record.summary ?? undefined,
    conclusion: record.conclusion ?? undefined,
    items: record.items.map((it) => ({
      id: it.id.startsWith("new-") ? undefined : it.id,
      item_type: it.item_type,
      location: it.location ?? undefined,
      description: it.description,
      legal_basis: it.legal_basis ?? undefined,
      correction_requirement: it.correction_requirement ?? undefined,
      severity: it.severity ?? undefined,
      sort_order: it.sort_order,
    })),
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
