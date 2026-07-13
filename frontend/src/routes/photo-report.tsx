import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { ErrorState, UnavailableState } from "@/components/common/StateViews";
import { photoReportService } from "@/lib/services/photo-report";
import { Loader2, Upload } from "lucide-react";

export const Route = createFileRoute("/photo-report")({
  head: () => ({
    meta: [
      { title: "图像报告 · 消防智能助手" },
      { name: "description", content: "上传检查视频,由后端抽取关键帧生成图像报告草稿。" },
    ],
  }),
  component: PhotoReportPage,
});

function PhotoReportPage() {
  const [file, setFile] = useState<File | null>(null);
  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (file) fd.append("video", file);
      return photoReportService.generate(fd);
    },
  });
  const taskId = mutation.data?.task_id ?? null;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="图像报告"
        description="上传检查视频,后端将抽取关键帧并识别地址、违规描述,供审阅编辑。"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">上传视频</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUpload
            accept="video/mp4,video/quicktime,.mp4,.mov"
            value={file}
            onChange={(v) => setFile(Array.isArray(v) ? v[0] ?? null : v)}
            hint="仅支持 mp4 / mov,单个文件"
            disabled={mutation.isPending}
          />
          <div className="flex justify-end">
            <Button
              onClick={() => mutation.mutate()}
              disabled={!file || mutation.isPending}
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
            <CardTitle className="text-sm">图像与说明</CardTitle>
          </CardHeader>
          <CardContent>
            <UnavailableState
              title="待任务完成后加载"
              description="后端返回图像与草稿字段后,此处将支持图片选择、排序、说明编辑与保存。"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
