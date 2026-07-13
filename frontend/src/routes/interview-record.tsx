import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { ErrorState, UnavailableState } from "@/components/common/StateViews";
import { interviewRecordService } from "@/lib/services/interview-record";
import { Loader2, Upload } from "lucide-react";

export const Route = createFileRoute("/interview-record")({
  head: () => ({
    meta: [
      { title: "询问笔录 · 消防智能助手" },
      { name: "description", content: "上传音视频,生成结构化询问笔录草稿。" },
    ],
  }),
  component: InterviewRecordPage,
});

function InterviewRecordPage() {
  const [audio, setAudio] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (audio) fd.append("audio", audio);
      if (video) fd.append("video", video);
      return interviewRecordService.generate(fd);
    },
  });
  const taskId = mutation.data?.task_id ?? null;
  const canSubmit = !!(audio || video) && !mutation.isPending;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="询问笔录"
        description="上传询问过程的音频或视频,后端将识别语音并生成结构化笔录草稿。"
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">上传录音或视频</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">音频</div>
              <FileUpload
                accept="audio/wav,audio/mpeg,audio/mp4,.wav,.mp3,.m4a"
                value={audio}
                onChange={(v) => setAudio(Array.isArray(v) ? v[0] ?? null : v)}
                hint="wav / mp3 / m4a"
                disabled={mutation.isPending}
              />
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">视频</div>
              <FileUpload
                accept="video/mp4,video/quicktime,.mp4,.mov"
                value={video}
                onChange={(v) => setVideo(Array.isArray(v) ? v[0] ?? null : v)}
                hint="mp4 / mov"
                disabled={mutation.isPending}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={() => mutation.mutate()} disabled={!canSubmit}>
              {mutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              提交生成
            </Button>
          </div>
          {mutation.error && (
            <ErrorState
              description={(mutation.error as Error).message}
              onRetry={() => mutation.mutate()}
            />
          )}
        </CardContent>
      </Card>

      {taskId && (
        <div className="mt-6">
          <TaskProgress taskId={taskId} />
        </div>
      )}

      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">笔录审阅</CardTitle>
          </CardHeader>
          <CardContent>
            <UnavailableState
              title="待任务完成后加载"
              description="后端返回转写文本与结构化字段后,此处将支持说话人核对与内容修订。"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
