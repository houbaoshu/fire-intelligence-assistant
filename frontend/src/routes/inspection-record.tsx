import { useCallback, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { PageHeader } from "@/components/layout/AppShell";
import { InspectionEditor } from "@/components/records/RecordEditors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { usePersistentTask } from "@/hooks/usePersistentTask";
import { inspectionRecordService } from "@/lib/services/inspection-record";
import type { TaskState } from "@/lib/services/tasks";

export const Route = createFileRoute("/inspection-record")({
  head: () => ({
    meta: [
      { title: "检查记录 · 消防智能助手" },
      { name: "description", content: "上传检查视频,生成结构化检查记录草稿并导出 Word。" },
    ],
  }),
  component: InspectionRecordPage,
});

function InspectionRecordPage() {
  const [file, setFile] = useState<File | null>(null);
  const [remarks, setRemarks] = useState("");
  const [taskId, setTaskId] = usePersistentTask("inspection-record");
  const [recordId, setRecordId] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (file) fd.append("video", file);
      if (remarks.trim()) fd.append("remarks", remarks.trim());
      return inspectionRecordService.generate(fd);
    },
    onSuccess: (result) => {
      setTaskId(result.task_id);
      setRecordId(result.entity_id ?? null);
    },
  });
  const onComplete = useCallback(
    (task: TaskState) => setRecordId(task.result?.entity_id ?? null),
    [],
  );
  const record = useQuery({
    queryKey: ["inspection-record", recordId],
    queryFn: ({ signal }) => inspectionRecordService.get(recordId!, signal),
    enabled: !!recordId,
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="检查记录"
        description="上传现场检查视频并审阅 AI 草稿。未配置相应模型时，任务会明确失败而不会编造内容。"
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">上传视频</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUpload
            accept="video/mp4,video/quicktime,.mp4,.mov"
            value={file}
            onChange={(value) => setFile(Array.isArray(value) ? (value[0] ?? null) : value)}
            hint="仅支持 mp4 / mov"
            disabled={mutation.isPending}
          />
          <div className="space-y-2">
            <Label htmlFor="remarks">检查员备注（可选，与机器证据分开保存）</Label>
            <Textarea id="remarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} />
          </div>
          <div className="flex justify-end">
            <Button onClick={() => mutation.mutate()} disabled={!file || mutation.isPending}>
              {mutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              提交生成
            </Button>
          </div>
          {mutation.error && (
            <ErrorState description={mutation.error.message} onRetry={() => mutation.mutate()} />
          )}
        </CardContent>
      </Card>
      {taskId && <TaskProgress className="mt-6" taskId={taskId} onComplete={onComplete} />}
      <div className="mt-6">
        {record.isLoading ? (
          <LoadingState title="正在加载草稿" />
        ) : record.error ? (
          <ErrorState description={record.error.message} onRetry={() => record.refetch()} />
        ) : record.data ? (
          <InspectionEditor initial={record.data} />
        ) : null}
      </div>
    </div>
  );
}
