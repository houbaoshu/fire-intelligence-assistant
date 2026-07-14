import { useCallback, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { PageHeader } from "@/components/layout/AppShell";
import { InterviewEditor } from "@/components/records/RecordEditors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePersistentTask } from "@/hooks/usePersistentTask";
import { interviewRecordService } from "@/lib/services/interview-record";
import type { TaskState } from "@/lib/services/tasks";

export const Route = createFileRoute("/interview-record")({
  head: () => ({ meta: [{ title: "询问笔录 · 消防智能助手" }] }),
  component: InterviewRecordPage,
});

function InterviewRecordPage() {
  const [audio, setAudio] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [taskId, setTaskId] = usePersistentTask("interview-record");
  const [recordId, setRecordId] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (audio) fd.append("audio", audio);
      if (video) fd.append("video", video);
      return interviewRecordService.generate(fd);
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
    queryKey: ["interview-record", recordId],
    queryFn: ({ signal }) => interviewRecordService.get(recordId!, signal),
    enabled: !!recordId,
  });

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="询问笔录"
        description="上传一份音频或视频；转写原文与结构化笔录始终分开显示。"
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">上传录音或视频（只能选择一种）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <FileUpload
              accept="audio/wav,audio/mpeg,audio/mp4,.wav,.mp3,.m4a"
              value={audio}
              onChange={(value) => {
                const selected = Array.isArray(value) ? (value[0] ?? null) : value;
                setAudio(selected);
                if (selected) setVideo(null);
              }}
              hint="wav / mp3 / m4a"
              disabled={mutation.isPending}
            />
            <FileUpload
              accept="video/mp4,video/quicktime,.mp4,.mov"
              value={video}
              onChange={(value) => {
                const selected = Array.isArray(value) ? (value[0] ?? null) : value;
                setVideo(selected);
                if (selected) setAudio(null);
              }}
              hint="mp4 / mov"
              disabled={mutation.isPending}
            />
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => mutation.mutate()}
              disabled={!(audio || video) || mutation.isPending}
            >
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
          <LoadingState title="正在加载笔录" />
        ) : record.error ? (
          <ErrorState description={record.error.message} onRetry={() => record.refetch()} />
        ) : record.data ? (
          <InterviewEditor initial={record.data} />
        ) : null}
      </div>
    </div>
  );
}
