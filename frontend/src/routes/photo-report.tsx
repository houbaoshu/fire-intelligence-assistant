import { useCallback, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { PageHeader } from "@/components/layout/AppShell";
import { PhotoReportEditor } from "@/components/records/RecordEditors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePersistentTask } from "@/hooks/usePersistentTask";
import { photoReportService } from "@/lib/services/photo-report";
import type { TaskState } from "@/lib/services/tasks";

export const Route = createFileRoute("/photo-report")({
  head: () => ({ meta: [{ title: "图像报告 · 消防智能助手" }] }),
  component: PhotoReportPage,
});

function PhotoReportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = usePersistentTask("photo-report");
  const [reportId, setReportId] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (file) fd.append("video", file);
      return photoReportService.generate(fd);
    },
    onSuccess: (result) => {
      setTaskId(result.task_id);
      setReportId(result.entity_id ?? null);
    },
  });
  const onComplete = useCallback(
    (task: TaskState) => setReportId(task.result?.entity_id ?? null),
    [],
  );
  const report = useQuery({
    queryKey: ["photo-report", reportId],
    queryFn: ({ signal }) => photoReportService.get(reportId!, signal),
    enabled: !!reportId,
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="图像报告"
        description="抽取代表性视频帧；每张图片、地址和问题描述都需人工核对。"
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
        {report.isLoading ? (
          <LoadingState title="正在加载报告" />
        ) : report.error ? (
          <ErrorState description={report.error.message} onRetry={() => report.refetch()} />
        ) : report.data ? (
          <PhotoReportEditor initial={report.data} />
        ) : null}
      </div>
    </div>
  );
}
