import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, ArrowDown, ArrowUp, Loader2, Plus, Save, Trash2 } from "lucide-react";
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
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { RecordStatusBadge } from "@/components/common/StatusBadges";
import { DocumentDownloadButton } from "@/components/common/DocumentDownloadButton";
import { RecordStatusActions } from "@/components/records/RecordStatusActions";
import { ApiError } from "@/lib/api-client";
import { useRecordEditor } from "@/hooks/useRecordEditor";
import {
  inspectionRecordService,
  INSPECTION_ITEM_TYPES,
  INSPECTION_SEVERITIES,
  type InspectionItemType,
  type InspectionRecordDetail,
  type InspectionRecordUpdate,
  type InspectionSeverity,
} from "@/lib/services/inspection-record";
import { ITEM_TYPE_LABELS, SEVERITY_LABELS } from "@/lib/labels";
import { fromLocalInputValue, toLocalInputValue } from "@/lib/datetime";

export const Route = createFileRoute("/inspection-record/$id")({
  head: () => ({
    meta: [
      { title: "检查记录详情 · 消防智能助手" },
      { name: "description", content: "审阅、编辑并保存结构化检查记录,下载后端生成的 Word 文书。" },
    ],
  }),
  component: InspectionRecordDetailPage,
});

type ItemForm = {
  /** 本地稳定 key;新增项在保存前没有后端 id。 */
  localId: string;
  id?: string;
  item_type: InspectionItemType;
  location: string;
  description: string;
  legal_basis: string;
  correction_requirement: string;
  severity: InspectionSeverity | "";
};

type FormState = {
  title: string;
  inspection_unit: string;
  inspection_address: string;
  inspection_date: string;
  inspector_names: string;
  contact_person: string;
  contact_phone: string;
  summary: string;
  conclusion: string;
  items: ItemForm[];
};

const SEVERITY_NONE = "__none__";

function toForm(detail: InspectionRecordDetail): FormState {
  return {
    title: detail.title ?? "",
    inspection_unit: detail.inspection_unit ?? "",
    inspection_address: detail.inspection_address ?? "",
    inspection_date: toLocalInputValue(detail.inspection_date),
    inspector_names: (detail.inspector_names ?? []).join(", "),
    contact_person: detail.contact_person ?? "",
    contact_phone: detail.contact_phone ?? "",
    summary: detail.summary ?? "",
    conclusion: detail.conclusion ?? "",
    items: [...detail.items]
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        localId: item.id,
        id: item.id,
        item_type: item.item_type,
        location: item.location ?? "",
        description: item.description,
        legal_basis: item.legal_basis ?? "",
        correction_requirement: item.correction_requirement ?? "",
        severity: item.severity ?? "",
      })),
  };
}

function buildPayload(form: FormState): InspectionRecordUpdate {
  return {
    title: form.title || null,
    inspection_unit: form.inspection_unit || null,
    inspection_address: form.inspection_address || null,
    inspection_date: form.inspection_date
      ? (fromLocalInputValue(form.inspection_date) ?? null)
      : null,
    inspector_names: form.inspector_names
      ? form.inspector_names
          .split(/[,，、;；]+/)
          .map((s) => s.trim())
          .filter(Boolean)
      : null,
    contact_person: form.contact_person || null,
    contact_phone: form.contact_phone || null,
    summary: form.summary || null,
    conclusion: form.conclusion || null,
    // items 为整体替换语义:新增不传 id,省略已有 id 即删除(API.md §4.1)。
    items: form.items.map((item, index) => ({
      ...(item.id ? { id: item.id } : {}),
      item_type: item.item_type,
      location: item.location || null,
      description: item.description,
      legal_basis: item.legal_basis || null,
      correction_requirement: item.correction_requirement || null,
      severity: item.severity || null,
      sort_order: index + 1,
    })),
  };
}

function InspectionRecordDetailPage() {
  const { id } = Route.useParams();
  const editor = useRecordEditor({
    queryKey: ["inspection-record", "detail", id],
    fetchDetail: (signal) => inspectionRecordService.get(id, signal),
    toForm,
    buildPayload,
    updateRecord: (payload) => inspectionRecordService.update(id, payload),
    setStatus: (status) => inspectionRecordService.update(id, { status }),
  });
  const { query, detail, form, dirty, update, discard, save, transition } = editor;

  if (query.isLoading || !form) {
    return (
      <div className="mx-auto max-w-4xl">
        <LoadingState title="加载记录详情…" />
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
          title="记录加载失败"
          description={query.error instanceof Error ? query.error.message : "加载失败"}
          onRetry={() => query.refetch()}
        />
      </div>
    );
  }

  const saveError = save.error;
  const isConflict = saveError instanceof ApiError && saveError.status === 409;

  const moveItem = (index: number, delta: number) =>
    update((f) => {
      const target = index + delta;
      if (target < 0 || target >= f.items.length) return f;
      const items = [...f.items];
      [items[index], items[target]] = [items[target], items[index]];
      return { ...f, items };
    });

  const removeItem = (index: number) =>
    update((f) => {
      const item = f.items[index];
      const hasContent = item.description || item.location || item.legal_basis;
      if (hasContent && !window.confirm("该检查项已有内容,确认删除?")) return f;
      return { ...f, items: f.items.filter((_, i) => i !== index) };
    });

  const addItem = () =>
    update((f) => ({
      ...f,
      items: [
        ...f.items,
        {
          localId: crypto.randomUUID(),
          item_type: "violation" as const,
          location: "",
          description: "",
          legal_basis: "",
          correction_requirement: "",
          severity: "",
        },
      ],
    }));

  const patchItem = (index: number, patch: Partial<ItemForm>) =>
    update((f) => ({
      ...f,
      items: f.items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            {detail?.title || "检查记录"}
            {detail && <RecordStatusBadge status={detail.status} />}
          </span>
        }
        description={
          detail?.record_number ? (
            <>
              记录编号:<span className="font-mono">{detail.record_number}</span>
              <span className="ml-3">AI 生成内容为草稿,请逐项核对后再保存 / 定稿。</span>
            </>
          ) : (
            "AI 生成内容为草稿,请逐项核对后再保存 / 定稿。"
          )
        }
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/inspection-record">
                <ArrowLeft className="mr-1 h-4 w-4" /> 返回列表
              </Link>
            </Button>
            {detail && (
              <DocumentDownloadButton
                fetchBlob={() => inspectionRecordService.download(id)}
                filename={`inspection-record-${detail.record_number ?? detail.id}.docx`}
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
            <Label htmlFor="inspection_unit">被检查单位</Label>
            <Input
              id="inspection_unit"
              value={form.inspection_unit}
              onChange={(e) => update((f) => ({ ...f, inspection_unit: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="inspection_date">检查日期</Label>
            <Input
              id="inspection_date"
              type="datetime-local"
              value={form.inspection_date}
              onChange={(e) => update((f) => ({ ...f, inspection_date: e.target.value }))}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="inspection_address">检查地址</Label>
            <Input
              id="inspection_address"
              value={form.inspection_address}
              onChange={(e) => update((f) => ({ ...f, inspection_address: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="inspector_names">检查人员(多人用逗号分隔)</Label>
            <Input
              id="inspector_names"
              value={form.inspector_names}
              onChange={(e) => update((f) => ({ ...f, inspector_names: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_person">联系人</Label>
            <Input
              id="contact_person"
              value={form.contact_person}
              onChange={(e) => update((f) => ({ ...f, contact_person: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_phone">联系电话</Label>
            <Input
              id="contact_phone"
              value={form.contact_phone}
              onChange={(e) => update((f) => ({ ...f, contact_phone: e.target.value }))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm">检查发现({form.items.length} 项)</CardTitle>
          <Button size="sm" variant="outline" onClick={addItem}>
            <Plus className="mr-1 h-4 w-4" /> 新增检查项
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {form.items.length === 0 && (
            <div className="text-sm text-muted-foreground">
              暂无检查发现。AI 未提取到问题项时可手动新增;不确定的内容请留空,不要凭推测填写。
            </div>
          )}
          {form.items.map((item, index) => (
            <div
              key={item.localId}
              className="space-y-3 rounded-lg border border-border bg-card/50 p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground">#{index + 1}</span>
                <Select
                  value={item.item_type}
                  onValueChange={(v) => patchItem(index, { item_type: v as InspectionItemType })}
                >
                  <SelectTrigger className="h-8 w-32" aria-label="发现项类型">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INSPECTION_ITEM_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {ITEM_TYPE_LABELS[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={item.severity || SEVERITY_NONE}
                  onValueChange={(v) =>
                    patchItem(index, {
                      severity: v === SEVERITY_NONE ? "" : (v as InspectionSeverity),
                    })
                  }
                >
                  <SelectTrigger className="h-8 w-28" aria-label="严重程度">
                    <SelectValue placeholder="严重程度" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={SEVERITY_NONE}>未标注</SelectItem>
                    {INSPECTION_SEVERITIES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {SEVERITY_LABELS[s]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  className="h-8 min-w-40 flex-1"
                  placeholder="发现位置"
                  value={item.location}
                  onChange={(e) => patchItem(index, { location: e.target.value })}
                />
                <div className="ml-auto flex items-center gap-1">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={() => moveItem(index, -1)}
                    disabled={index === 0}
                    aria-label="上移"
                  >
                    <ArrowUp className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={() => moveItem(index, 1)}
                    disabled={index === form.items.length - 1}
                    aria-label="下移"
                  >
                    <ArrowDown className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive"
                    onClick={() => removeItem(index)}
                    aria-label="删除检查项"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <Textarea
                rows={2}
                placeholder="发现描述"
                value={item.description}
                onChange={(e) => patchItem(index, { description: e.target.value })}
              />
              <div className="grid gap-3 md:grid-cols-2">
                <Textarea
                  rows={2}
                  placeholder="法律依据(须来自权威材料,不确定请留空)"
                  value={item.legal_basis}
                  onChange={(e) => patchItem(index, { legal_basis: e.target.value })}
                />
                <Textarea
                  rows={2}
                  placeholder="整改要求"
                  value={item.correction_requirement}
                  onChange={(e) => patchItem(index, { correction_requirement: e.target.value })}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">概述与结论</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="summary">检查情况概述</Label>
            <Textarea
              id="summary"
              rows={4}
              value={form.summary}
              onChange={(e) => update((f) => ({ ...f, summary: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="conclusion">检查结论</Label>
            <Textarea
              id="conclusion"
              rows={3}
              value={form.conclusion}
              onChange={(e) => update((f) => ({ ...f, conclusion: e.target.value }))}
            />
          </div>
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
