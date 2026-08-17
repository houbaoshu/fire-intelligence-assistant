import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowDown, ArrowLeft, ArrowUp, Image as ImageIcon, Loader2, Save } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { RecordStatusBadge } from "@/components/common/StatusBadges";
import { DocumentDownloadButton } from "@/components/common/DocumentDownloadButton";
import { RecordStatusActions } from "@/components/records/RecordStatusActions";
import { ApiError } from "@/lib/api-client";
import { useRecordEditor } from "@/hooks/useRecordEditor";
import {
  photoReportService,
  type PhotoReportDetail,
  type PhotoReportUpdate,
} from "@/lib/services/photo-report";

export const Route = createFileRoute("/photo-report/$id")({
  head: () => ({
    meta: [
      { title: "图像报告详情 · 消防智能助手" },
      {
        name: "description",
        content: "审阅图片集、编辑 caption 与选择入档图片,下载后端生成的 Word 文档。",
      },
    ],
  }),
  component: PhotoReportDetailPage,
});

type ImageForm = {
  id: string;
  frame_timestamp: number | null;
  detected_address: string | null;
  detected_violation: string | null;
  caption: string;
  is_selected: boolean;
};

type FormState = {
  title: string;
  inspection_unit: string;
  inspection_address: string;
  violation_summary: string;
  images: ImageForm[];
};

function toForm(detail: PhotoReportDetail): FormState {
  return {
    title: detail.title ?? "",
    inspection_unit: detail.inspection_unit ?? "",
    inspection_address: detail.inspection_address ?? "",
    violation_summary: detail.violation_summary ?? "",
    images: [...detail.images]
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((img) => ({
        id: img.id,
        frame_timestamp: img.frame_timestamp,
        detected_address: img.detected_address,
        detected_violation: img.detected_violation,
        caption: img.caption ?? "",
        is_selected: img.is_selected,
      })),
  };
}

function buildPayload(form: FormState): PhotoReportUpdate {
  return {
    title: form.title || null,
    inspection_unit: form.inspection_unit || null,
    inspection_address: form.inspection_address || null,
    violation_summary: form.violation_summary || null,
    // 图片按 id 逐项更新,仅 caption / is_selected / sort_order 可编辑(API.md §4.2);
    // sort_order 按当前展示顺序归一化为 1..n,保证唯一。
    images: form.images.map((img, index) => ({
      id: img.id,
      caption: img.caption || null,
      is_selected: img.is_selected,
      sort_order: index + 1,
    })),
  };
}

function formatTimestamp(seconds: number | null): string {
  if (seconds === null || Number.isNaN(seconds)) return "未知时间点";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `源视频 ${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function PhotoReportDetailPage() {
  const { id } = Route.useParams();
  const { query, detail, form, dirty, update, discard, save, transition } = useRecordEditor({
    queryKey: ["photo-report", "detail", id],
    fetchDetail: (signal) => photoReportService.get(id, signal),
    toForm,
    buildPayload,
    updateRecord: (payload) => photoReportService.update(id, payload),
    setStatus: (status) => photoReportService.update(id, { status }),
  });

  if (query.isLoading || !form) {
    return (
      <div className="mx-auto max-w-4xl">
        <LoadingState title="加载报告详情…" />
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
          title="报告加载失败"
          description={query.error instanceof Error ? query.error.message : "加载失败"}
          onRetry={() => query.refetch()}
        />
      </div>
    );
  }

  const saveError = save.error;
  const isConflict = saveError instanceof ApiError && saveError.status === 409;
  const selectedCount = form.images.filter((img) => img.is_selected).length;
  const finalizeBlocker = selectedCount === 0 ? "至少选中一张入档图片才能定稿 / 生成文档" : null;

  const moveImage = (index: number, delta: number) =>
    update((f) => {
      const target = index + delta;
      if (target < 0 || target >= f.images.length) return f;
      const images = [...f.images];
      [images[index], images[target]] = [images[target], images[index]];
      return { ...f, images };
    });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            {detail?.title || "图像报告"}
            {detail && <RecordStatusBadge status={detail.status} />}
          </span>
        }
        description="AI 识别的 caption、地址与违规均为草稿,请逐张核对;仅选中的图片进入最终文档。"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/photo-report">
                <ArrowLeft className="mr-1 h-4 w-4" /> 返回列表
              </Link>
            </Button>
            {detail && (
              <DocumentDownloadButton
                fetchBlob={() => photoReportService.download(id)}
                filename={`photo-report-${detail.id}.docx`}
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
              <span>报告可能已被他人修改或已定稿,为避免覆盖请重新加载最新内容。</span>
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
          <CardTitle className="text-sm">报告信息</CardTitle>
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
            <Label htmlFor="inspection_unit">被检查单位</Label>
            <Input
              id="inspection_unit"
              value={form.inspection_unit}
              onChange={(e) => update((f) => ({ ...f, inspection_unit: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="inspection_address">检查地址</Label>
            <Input
              id="inspection_address"
              value={form.inspection_address}
              onChange={(e) => update((f) => ({ ...f, inspection_address: e.target.value }))}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="violation_summary">隐患概述</Label>
            <Textarea
              id="violation_summary"
              rows={3}
              value={form.violation_summary}
              onChange={(e) => update((f) => ({ ...f, violation_summary: e.target.value }))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            图片集(共 {form.images.length} 张,已选中 {selectedCount} 张入档)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.images.length === 0 && (
            <div className="text-sm text-muted-foreground">
              暂无候选帧图片。抽帧筛选结果由后端生成;如需补充请重新提交生成任务。
            </div>
          )}
          {form.images.map((img, index) => (
            <div
              key={img.id}
              className="flex flex-col gap-3 rounded-lg border border-border bg-card/50 p-4 md:flex-row"
            >
              <div className="flex w-full shrink-0 flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border bg-muted/40 px-4 py-6 text-center md:w-44">
                <ImageIcon className="h-6 w-6 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">
                  {formatTimestamp(img.frame_timestamp)}
                </span>
                <span className="text-[10px] text-muted-foreground">图片预览由后端提供</span>
              </div>
              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={img.is_selected}
                      onCheckedChange={(v) =>
                        update((f) => ({
                          ...f,
                          images: f.images.map((it, i) =>
                            i === index ? { ...it, is_selected: v === true } : it,
                          ),
                        }))
                      }
                      aria-label={`图片 ${index + 1} 纳入文档`}
                    />
                    纳入文档
                  </label>
                  <span className="text-xs text-muted-foreground">#{index + 1}</span>
                  <div className="ml-auto flex items-center gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => moveImage(index, -1)}
                      disabled={index === 0}
                      aria-label="上移"
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => moveImage(index, 1)}
                      disabled={index === form.images.length - 1}
                      aria-label="下移"
                    >
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <Textarea
                  rows={2}
                  placeholder="图片说明(caption):简洁、客观描述可见的主要问题"
                  value={img.caption}
                  onChange={(e) =>
                    update((f) => ({
                      ...f,
                      images: f.images.map((it, i) =>
                        i === index ? { ...it, caption: e.target.value } : it,
                      ),
                    }))
                  }
                />
                <dl className="grid gap-1 text-xs text-muted-foreground md:grid-cols-2">
                  <div>
                    识别地址(供核对):
                    <span className="text-foreground">{img.detected_address ?? "未识别"}</span>
                  </div>
                  <div>
                    识别违规(供核对):
                    <span className="text-foreground">{img.detected_violation ?? "未识别"}</span>
                  </div>
                </dl>
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
            finalizeBlocker={finalizeBlocker}
            onMarkReviewed={() => transition.mutate("reviewed")}
            onFinalize={() => {
              if (window.confirm("定稿后报告将进入已定稿状态,后续修改可能被拒绝(409)。确认定稿?"))
                transition.mutate("finalized");
            }}
          />
          <Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
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
