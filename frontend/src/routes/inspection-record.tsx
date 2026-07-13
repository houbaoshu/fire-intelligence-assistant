import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { ErrorState, UnavailableState } from "@/components/common/StateViews";
import { inspectionRecordService } from "@/lib/services/inspection-record";
import { Loader2, Upload } from "lucide-react";

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
  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (file) fd.append("video", file);
      if (remarks.trim()) fd.append("remarks", remarks.trim());
      return inspectionRecordService.generate(fd);
    },
  });

  const taskId = mutation.data?.task_id ?? null;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="检查记录"
        description="上传一段现场检查视频与可选备注,提交后由后端异步生成结构化草稿。"
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
          <div className="space-y-2">
            <Label htmlFor="remarks">备注(可选)</Label>
            <Textarea
              id="remarks"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              rows={3}
              placeholder="填写检查地点、现场情况等补充信息"
              disabled={mutation.isPending}
            />
          </div>
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
            <CardTitle className="text-sm">草稿审阅</CardTitle>
          </CardHeader>
          <CardContent>
            <UnavailableState
              title="待任务完成后加载"
              description="后端返回结构化字段后,此处将支持基本信息与检查发现的审阅、编辑与保存。"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
