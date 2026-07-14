import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Download, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ProtectedImage } from "@/components/common/ProtectedImage";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { saveBlob } from "@/lib/api-client";
import {
  inspectionRecordService,
  type InspectionFinding,
  type InspectionRecord,
} from "@/lib/services/inspection-record";
import { interviewRecordService, type InterviewRecord } from "@/lib/services/interview-record";
import { photoReportService, type PhotoReport } from "@/lib/services/photo-report";

function useUnsavedChanges(dirty: boolean) {
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string | null | undefined;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

export function InspectionEditor({ initial }: { initial: InspectionRecord }) {
  const [record, setRecord] = useState(initial);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    setRecord(initial);
    setDirty(false);
  }, [initial]);
  useUnsavedChanges(dirty);
  const update = <K extends keyof InspectionRecord>(key: K, value: InspectionRecord[K]) => {
    setRecord((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };
  const save = useMutation({
    mutationFn: () => inspectionRecordService.update(record.id, record),
    onSuccess: (saved) => {
      setRecord(saved);
      setDirty(false);
      toast.success("检查记录已保存");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const download = useMutation({
    mutationFn: () => inspectionRecordService.download(record.id),
    onSuccess: (blob) => saveBlob(blob, `inspection-record-${record.id}.docx`),
    onError: (error: Error) => toast.error(error.message),
  });

  const updateFinding = (index: number, patch: Partial<InspectionFinding>) => {
    update(
      "findings",
      record.findings.map((finding, itemIndex) =>
        itemIndex === index ? { ...finding, ...patch } : finding,
      ),
    );
  };
  const removeFinding = (index: number) => {
    if (!window.confirm("确定删除这条检查发现吗？")) return;
    update(
      "findings",
      record.findings.filter((_, itemIndex) => itemIndex !== index),
    );
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">草稿审阅</CardTitle>
        {dirty && <span className="text-xs text-amber-700">有未保存修改</span>}
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="标题" value={record.title} onChange={(value) => update("title", value)} />
          <Field
            label="记录编号"
            value={record.record_number}
            onChange={(value) => update("record_number", value)}
          />
          <Field
            label="被检查单位"
            value={record.inspection_unit}
            onChange={(value) => update("inspection_unit", value)}
          />
          <Field
            label="检查地址"
            value={record.inspection_address}
            onChange={(value) => update("inspection_address", value)}
          />
          <Field
            label="检查人员（顿号分隔）"
            value={record.inspector_names.join("、")}
            onChange={(value) =>
              update(
                "inspector_names",
                value
                  .split(/[、,]/)
                  .map((item) => item.trim())
                  .filter(Boolean),
              )
            }
          />
          <Field
            label="联系人"
            value={record.contact_person}
            onChange={(value) => update("contact_person", value)}
          />
          <Field
            label="联系电话"
            value={record.contact_phone}
            onChange={(value) => update("contact_phone", value)}
          />
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">检查发现</h3>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                update("findings", [
                  ...record.findings,
                  { item_type: "observation", description: "", sort_order: record.findings.length },
                ])
              }
            >
              <Plus className="mr-1 h-4 w-4" /> 添加
            </Button>
          </div>
          {record.findings.map((finding, index) => (
            <div key={finding.id ?? index} className="space-y-3 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">发现 {index + 1}</span>
                <Button size="icon" variant="ghost" onClick={() => removeFinding(index)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-1 text-xs">
                  <span>类型</span>
                  <select
                    className="h-9 w-full rounded-md border bg-background px-2"
                    value={finding.item_type}
                    onChange={(event) =>
                      updateFinding(index, {
                        item_type: event.target.value as InspectionFinding["item_type"],
                      })
                    }
                  >
                    <option value="observation">观察</option>
                    <option value="compliant">符合</option>
                    <option value="violation">违法</option>
                    <option value="hazard">隐患</option>
                    <option value="recommendation">建议</option>
                  </select>
                </label>
                <Field
                  label="位置"
                  value={finding.location}
                  onChange={(value) => updateFinding(index, { location: value })}
                />
              </div>
              <Textarea
                aria-label={`发现 ${index + 1} 描述`}
                value={finding.description}
                onChange={(event) => updateFinding(index, { description: event.target.value })}
                placeholder="客观描述可见事实"
              />
              <Textarea
                aria-label={`发现 ${index + 1} 法律依据`}
                value={finding.legal_basis ?? ""}
                onChange={(event) => updateFinding(index, { legal_basis: event.target.value })}
                placeholder="仅填写已核对的法律依据"
              />
              <Textarea
                aria-label={`发现 ${index + 1} 整改要求`}
                value={finding.correction_requirement ?? ""}
                onChange={(event) =>
                  updateFinding(index, { correction_requirement: event.target.value })
                }
                placeholder="整改要求"
              />
            </div>
          ))}
        </div>
        {record.source_notes && (
          <div className="space-y-1.5">
            <Label>检查员原始备注（与 AI 草稿分开）</Label>
            <div className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
              {record.source_notes}
            </div>
          </div>
        )}
        <div className="space-y-1.5">
          <Label>检查摘要</Label>
          <Textarea
            value={record.summary ?? ""}
            onChange={(e) => update("summary", e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>检查结论</Label>
          <Textarea
            value={record.conclusion ?? ""}
            onChange={(e) => update("conclusion", e.target.value)}
          />
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => download.mutate()}
            disabled={dirty || download.isPending}
          >
            <Download className="mr-2 h-4 w-4" /> 下载 Word
          </Button>
          <Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
            <Save className="mr-2 h-4 w-4" /> 保存修改
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function PhotoReportEditor({ initial }: { initial: PhotoReport }) {
  const [report, setReport] = useState(initial);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    setReport(initial);
    setDirty(false);
  }, [initial]);
  useUnsavedChanges(dirty);
  const update = <K extends keyof PhotoReport>(key: K, value: PhotoReport[K]) => {
    setReport((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };
  const save = useMutation({
    mutationFn: () => photoReportService.update(report.id, report),
    onSuccess: (saved) => {
      setReport(saved);
      setDirty(false);
      toast.success("图像报告已保存");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const download = useMutation({
    mutationFn: () => photoReportService.download(report.id),
    onSuccess: (blob) => saveBlob(blob, `photo-report-${report.id}.docx`),
    onError: (error: Error) => toast.error(error.message),
  });
  const ordered = useMemo(
    () => [...report.images].sort((a, b) => a.sort_order - b.sort_order),
    [report],
  );
  const patchImage = (id: string, patch: Partial<PhotoReport["images"][number]>) =>
    update(
      "images",
      report.images.map((image) => (image.id === id ? { ...image, ...patch } : image)),
    );
  const move = (index: number, delta: number) => {
    const next = [...ordered];
    const target = index + delta;
    if (!next[target]) return;
    [next[index], next[target]] = [next[target], next[index]];
    update(
      "images",
      next.map((image, itemIndex) => ({ ...image, sort_order: itemIndex })),
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">图像与说明审阅</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="标题" value={report.title} onChange={(value) => update("title", value)} />
          <Field
            label="被检查单位"
            value={report.inspection_unit}
            onChange={(value) => update("inspection_unit", value)}
          />
          <Field
            label="检查地址"
            value={report.inspection_address}
            onChange={(value) => update("inspection_address", value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>问题摘要</Label>
          <Textarea
            value={report.violation_summary ?? ""}
            onChange={(event) => update("violation_summary", event.target.value)}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {ordered.map((image, index) => (
            <div key={image.id} className="space-y-3 rounded-md border p-3">
              <ProtectedImage
                reportId={report.id}
                imageId={image.id}
                alt={image.caption || `证据图片 ${index + 1}`}
              />
              <div className="flex items-center justify-between gap-2">
                <label className="flex items-center gap-2 text-xs">
                  <Checkbox
                    checked={image.is_selected}
                    onCheckedChange={(checked) =>
                      patchImage(image.id, { is_selected: checked === true })
                    }
                  />
                  纳入报告
                </label>
                <div>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => move(index, -1)}
                    aria-label="上移"
                  >
                    <ArrowUp className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => move(index, 1)}
                    aria-label="下移"
                  >
                    <ArrowDown className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {image.needs_review && <p className="text-xs text-amber-700">需要人工核对</p>}
              <Textarea
                aria-label="图片说明"
                value={image.caption ?? ""}
                onChange={(event) =>
                  patchImage(image.id, { caption: event.target.value, needs_review: false })
                }
              />
              <Input
                aria-label="识别地址"
                value={image.detected_address ?? ""}
                onChange={(event) => patchImage(image.id, { detected_address: event.target.value })}
              />
              <Textarea
                aria-label="问题描述"
                value={image.detected_violation ?? ""}
                onChange={(event) =>
                  patchImage(image.id, { detected_violation: event.target.value })
                }
              />
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" disabled={dirty} onClick={() => download.mutate()}>
            <Download className="mr-2 h-4 w-4" /> 下载 Word
          </Button>
          <Button disabled={!dirty} onClick={() => save.mutate()}>
            <Save className="mr-2 h-4 w-4" /> 保存修改
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function InterviewEditor({ initial }: { initial: InterviewRecord }) {
  const [record, setRecord] = useState(initial);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    setRecord(initial);
    setDirty(false);
  }, [initial]);
  useUnsavedChanges(dirty);
  const update = <K extends keyof InterviewRecord>(key: K, value: InterviewRecord[K]) => {
    setRecord((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };
  const sections = record.structured_content.sections ?? [];
  const updateSections = (next: typeof sections) =>
    update("structured_content", { ...record.structured_content, sections: next });
  const save = useMutation({
    mutationFn: () => interviewRecordService.update(record.id, record),
    onSuccess: (saved) => {
      setRecord(saved);
      setDirty(false);
      toast.success("询问笔录已保存");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const download = useMutation({
    mutationFn: () => interviewRecordService.download(record.id),
    onSuccess: (blob) => saveBlob(blob, `interview-record-${record.id}.docx`),
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">笔录审阅</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="标题" value={record.title} onChange={(value) => update("title", value)} />
          <Field
            label="被询问人"
            value={record.interviewee_name}
            onChange={(value) => update("interviewee_name", value)}
          />
          <Field
            label="询问人员（顿号分隔）"
            value={record.interviewer_names.join("、")}
            onChange={(value) =>
              update(
                "interviewer_names",
                value
                  .split(/[、,]/)
                  .map((item) => item.trim())
                  .filter(Boolean),
              )
            }
          />
          <Field
            label="询问地点"
            value={record.location}
            onChange={(value) => update("location", value)}
          />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-2">
            <Label>机器转写（证据原文，只读）</Label>
            <div className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
              {record.transcript || "未返回可用转写"}
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>结构化问答</Label>
              <Button size="sm" variant="outline" onClick={() => updateSections([...sections, {}])}>
                <Plus className="mr-1 h-4 w-4" /> 添加
              </Button>
            </div>
            {sections.map((section, index) => (
              <div key={index} className="space-y-2 rounded-md border p-3">
                <Input
                  value={section.question ?? ""}
                  placeholder="问题"
                  onChange={(event) =>
                    updateSections(
                      sections.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, question: event.target.value } : item,
                      ),
                    )
                  }
                />
                <Textarea
                  value={section.answer ?? ""}
                  placeholder="回答"
                  onChange={(event) =>
                    updateSections(
                      sections.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, answer: event.target.value } : item,
                      ),
                    )
                  }
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    updateSections(sections.filter((_, itemIndex) => itemIndex !== index))
                  }
                >
                  <Trash2 className="mr-1 h-4 w-4" /> 删除
                </Button>
              </div>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" disabled={dirty} onClick={() => download.mutate()}>
            <Download className="mr-2 h-4 w-4" /> 下载 Word
          </Button>
          <Button disabled={!dirty} onClick={() => save.mutate()}>
            <Save className="mr-2 h-4 w-4" /> 保存修改
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
