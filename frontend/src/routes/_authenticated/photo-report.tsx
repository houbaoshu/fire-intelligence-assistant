import { createFileRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  FileCheck2,
  Images,
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
import { Switch } from "@/components/ui/switch";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { RecordStatusBadge } from "@/components/common/RecordStatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import {
  photoReportService,
  type PhotoReport,
  type PhotoReportUpdate,
} from "@/lib/services/photo-report";
import { RECORD_STATUS_LABELS } from "@/lib/record-status";
import { ApiError } from "@/lib/api-client";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/photo-report")({
  head: () => ({
    meta: [
      { title: "拍照报告 · 消防智能助手" },
      { name: "description", content: "上传检查视频,由后端抽取关键帧生成拍照报告草稿。" },
    ],
  }),
  component: PhotoReportPage,
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

function PhotoReportPage() {
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
    queryKey: ["photo-reports", { status }],
    queryFn: ({ signal }) =>
      photoReportService.list({ page: 1, page_size: 50, status: status || undefined }, signal),
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="拍照报告"
        description="上传检查视频,后端抽取关键帧并识别地址、违规描述,供审阅编辑后导出文书。"
        actions={
          <Button onClick={() => navigate({ to: "/photo-report", search: { action: "new" } })}>
            <Plus className="mr-2 h-4 w-4" /> 新建拍照报告
          </Button>
        }
      />
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">报告列表</CardTitle>
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
            <LoadingState description="正在加载报告…" />
          ) : query.isError ? (
            <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
          ) : query.data && query.data.items.length === 0 ? (
            <EmptyState
              title="还没有拍照报告"
              description="点击右上角「新建拍照报告」上传检查视频开始生成。"
            />
          ) : (
            <div className="divide-y">
              {query.data?.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate({ to: "/photo-report", search: { id: item.id } })}
                  className="flex w-full items-center justify-between gap-3 py-3 text-left transition hover:bg-accent/40"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">
                        {item.title || item.inspection_unit || "未命名报告"}
                      </span>
                      <RecordStatusBadge status={item.status} />
                    </div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {item.inspection_unit ? item.inspection_unit + " · " : ""}
                      {new Date(item.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                  <Images className="h-4 w-4 shrink-0 text-muted-foreground" />
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
      return photoReportService.generate(fd);
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
      toast.success("拍照报告生成完成");
      if (typeof recordId === "string") {
        navigate({ to: "/photo-report", search: { id: recordId } });
      }
    },
    [navigate],
  );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="新建拍照报告"
        description="上传一段检查视频,后端将抽取关键帧并生成照片说明草稿。"
        actions={
          <Button variant="outline" onClick={() => navigate({ to: "/photo-report" })}>
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
            <div className="flex justify-end">
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
  const [report, setReport] = useState<PhotoReport | null>(null);
  const [dirty, setDirty] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["photo-report", id],
    queryFn: ({ signal }) => photoReportService.get(id, signal),
    enabled: !!id,
  });

  useEffect(() => {
    if (detailQuery.data) {
      setReport(detailQuery.data);
      setDirty(false);
    }
  }, [detailQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (patch: PhotoReportUpdate) => photoReportService.update(id, patch),
    onSuccess: (updated) => {
      setReport(updated);
      setDirty(false);
      toast.success("已保存");
      qc.invalidateQueries({ queryKey: ["photo-reports"] });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) {
        toast.error("报告已定稿,不能直接修改");
      } else {
        toast.error("保存失败:" + e.message);
      }
    },
  });

  const onTaskComplete = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["photo-report", id] });
    detailQuery.refetch();
    toast.success("文书生成完成");
  }, [qc, id, detailQuery]);

  const patchReport = (patch: Partial<PhotoReport>) => {
    setReport((prev) => (prev ? { ...prev, ...patch } : prev));
    setDirty(true);
  };

  const patchImage = (index: number, patch: Record<string, unknown>) => {
    setReport((prev) => {
      if (!prev) return prev;
      const images = prev.images.map((img, i) => (i === index ? { ...img, ...patch } : img));
      return { ...prev, images };
    });
    setDirty(true);
  };

  const moveImage = (index: number, dir: -1 | 1) => {
    setReport((prev) => {
      if (!prev) return prev;
      const images = [...prev.images];
      const target = index + dir;
      if (target < 0 || target >= images.length) return prev;
      [images[index], images[target]] = [images[target], images[index]];
      return { ...prev, images };
    });
    setDirty(true);
  };

  const download = async () => {
    const tok = localStorage.getItem("fip.auth.access_token");
    try {
      const res = await fetch(photoReportService.downloadUrl(id), {
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
      a.download = "photo-report-" + id + ".docx";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      toast.error("下载失败:" + (e as Error).message);
    }
  };

  const isFinalized = report?.status === "finalized";
  const isProcessing = report?.status === "processing";
  const canEdit = !isFinalized && !isProcessing;
  const activeTaskId = isProcessing ? report?.source_task_id : null;
  const selectedCount = report?.images.filter((i) => i.is_selected).length ?? 0;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="拍照报告"
        description={report?.title || "加载中…"}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate({ to: "/photo-report" })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> 返回列表
            </Button>
            {report?.status === "finalized" && (
              <Button onClick={download}>
                <Download className="mr-2 h-4 w-4" /> 下载文书
              </Button>
            )}
          </>
        }
      />
      {detailQuery.isLoading && <LoadingState description="正在加载报告详情…" />}
      {detailQuery.isError && !report && (
        <ErrorState description={detailQuery.error.message} onRetry={() => detailQuery.refetch()} />
      )}
      {activeTaskId && (
        <TaskProgress
          taskId={activeTaskId}
          onComplete={onTaskComplete}
          onFail={() => toast.error("生成失败,请查看任务详情")}
        />
      )}
      {report && (
        <>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-sm">报告信息</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">已选 {selectedCount} 张</span>
                <RecordStatusBadge status={report.status} />
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Field label="标题">
                <Input
                  value={report.title ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchReport({ title: e.target.value })}
                />
              </Field>
              <Field label="被检查单位">
                <Input
                  value={report.inspection_unit ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchReport({ inspection_unit: e.target.value })}
                />
              </Field>
              <Field label="检查地址">
                <Input
                  value={report.inspection_address ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchReport({ inspection_address: e.target.value })}
                />
              </Field>
              <Field label="违规情况摘要" full>
                <Textarea
                  rows={3}
                  value={report.violation_summary ?? ""}
                  disabled={!canEdit}
                  onChange={(e) => patchReport({ violation_summary: e.target.value })}
                />
              </Field>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-sm">照片集(仅选中照片进入最终文档)</CardTitle>
            </CardHeader>
            <CardContent>
              {report.images.length === 0 ? (
                <EmptyState title="暂无照片" description="AI 抽帧未产出可用照片,或仍在处理中。" />
              ) : (
                <div className="space-y-4">
                  {report.images.map((img, idx) => (
                    <div
                      key={img.id}
                      className={
                        "rounded-lg border p-3 " +
                        (img.is_selected ? "border-border" : "border-dashed opacity-60")
                      }
                    >
                      <div className="flex flex-wrap items-start gap-4">
                        <img
                          src={photoReportService.imageUrl(img.uploaded_file_id)}
                          alt={img.caption || "检查现场照片"}
                          className="h-32 w-48 shrink-0 rounded-md border border-border object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <div className="text-xs text-muted-foreground">
                              照片 {idx + 1}
                              {img.frame_timestamp !== null &&
                              typeof img.frame_timestamp === "number"
                                ? " · 视频时间点 " + img.frame_timestamp.toFixed(1) + "s"
                                : ""}
                            </div>
                            <div className="flex items-center gap-3">
                              <label className="flex items-center gap-1.5 text-xs">
                                <Switch
                                  checked={img.is_selected}
                                  disabled={!canEdit}
                                  onCheckedChange={(v) => patchImage(idx, { is_selected: v })}
                                />
                                纳入文档
                              </label>
                              <div className="flex gap-1">
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7"
                                  disabled={!canEdit || idx === 0}
                                  onClick={() => moveImage(idx, -1)}
                                  aria-label="上移"
                                >
                                  ↑
                                </Button>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7"
                                  disabled={!canEdit || idx === report.images.length - 1}
                                  onClick={() => moveImage(idx, 1)}
                                  aria-label="下移"
                                >
                                  ↓
                                </Button>
                              </div>
                            </div>
                          </div>
                          <Field label="照片说明(caption)">
                            <Textarea
                              rows={2}
                              value={img.caption ?? ""}
                              disabled={!canEdit}
                              onChange={(e) => patchImage(idx, { caption: e.target.value })}
                            />
                          </Field>
                          <div className="grid gap-2 md:grid-cols-2">
                            <Field label="识别地址">
                              <Input
                                value={img.detected_address ?? ""}
                                disabled={!canEdit}
                                onChange={(e) =>
                                  patchImage(idx, { detected_address: e.target.value })
                                }
                              />
                            </Field>
                            <Field label="识别违规">
                              <Input
                                value={img.detected_violation ?? ""}
                                disabled={!canEdit}
                                onChange={(e) =>
                                  patchImage(idx, { detected_violation: e.target.value })
                                }
                              />
                            </Field>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-center justify-end gap-2">
            {dirty && <span className="text-xs text-muted-foreground">有未保存的更改</span>}
            {canEdit && (
              <Button
                onClick={() => saveMutation.mutate(collectPatch(report))}
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
            {canEdit && selectedCount > 0 && (
              <Button
                onClick={() => saveMutation.mutate({ status: "finalized" })}
                disabled={saveMutation.isPending}
              >
                <FileCheck2 className="mr-2 h-4 w-4" /> 定稿并生成文书
              </Button>
            )}
            {report.status === "finalized" && (
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

function collectPatch(report: PhotoReport): PhotoReportUpdate {
  return {
    title: report.title ?? undefined,
    inspection_unit: report.inspection_unit ?? undefined,
    inspection_address: report.inspection_address ?? undefined,
    violation_summary: report.violation_summary ?? undefined,
    images: report.images.map((img, idx) => ({
      id: img.id,
      caption: img.caption ?? undefined,
      is_selected: img.is_selected,
      sort_order: idx,
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
