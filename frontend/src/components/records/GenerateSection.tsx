import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { FileUpload } from "@/components/common/FileUpload";
import { TaskProgress } from "@/components/common/TaskProgress";
import { ErrorState } from "@/components/common/StateViews";
import { useResumableTask } from "@/hooks/useResumableTask";
import type { GenerateResponse } from "@/lib/services/common";
import type { Task } from "@/lib/services/tasks";

export type GenerateSectionProps = {
  /** 任务恢复用的 localStorage 键后缀(每个业务模块唯一)。 */
  storageKey: string;
  /** multipart 文件字段名(API.md §4:video / audio)。 */
  fileField: "video" | "audio";
  cardTitle: string;
  accept: string;
  maxSize: number;
  hint: string;
  remarksPlaceholder: string;
  generate: (form: FormData) => Promise<GenerateResponse>;
  /** 任务 completed 且 result_data.record_id 存在时回调,由页面负责跳转详情。 */
  onRecordReady: (recordId: string) => void;
};

/**
 * 上传素材 + 备注 + 提交异步生成任务的共享区块。
 * 任务 ID 持久化,页面刷新 / 重进后自动恢复轮询;completed 后按 result_data.record_id 跳转详情。
 */
export function GenerateSection({
  storageKey,
  fileField,
  cardTitle,
  accept,
  maxSize,
  hint,
  remarksPlaceholder,
  generate,
  onRecordReady,
}: GenerateSectionProps) {
  const [file, setFile] = useState<File | null>(null);
  const [remarks, setRemarks] = useState("");
  const { taskId, setTaskId } = useResumableTask(storageKey);

  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (file) fd.append(fileField, file);
      if (remarks.trim()) fd.append("remarks", remarks.trim());
      return generate(fd);
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
      mutation.reset();
    },
  });

  const handleComplete = (task: Task) => {
    const recordId = task.result_data?.record_id;
    setTaskId(null);
    if (recordId) onRecordReady(recordId);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{cardTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <FileUpload
          accept={accept}
          maxSize={maxSize}
          value={file}
          onChange={(v) => setFile(Array.isArray(v) ? (v[0] ?? null) : v)}
          hint={hint}
          disabled={mutation.isPending || !!taskId}
        />
        <div className="space-y-2">
          <Label htmlFor={`${storageKey}-remarks`}>备注(可选,仅作为检查人员补充说明)</Label>
          <Textarea
            id={`${storageKey}-remarks`}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
            rows={3}
            placeholder={remarksPlaceholder}
            disabled={mutation.isPending || !!taskId}
          />
        </div>
        <div className="flex justify-end">
          <Button
            onClick={() => mutation.mutate()}
            disabled={!file || mutation.isPending || !!taskId}
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

        {taskId && (
          <TaskProgress
            taskId={taskId}
            onComplete={handleComplete}
            footer={
              <div className="flex justify-end">
                <Button size="sm" variant="ghost" onClick={() => setTaskId(null)}>
                  清除任务记录
                </Button>
              </div>
            }
          />
        )}
      </CardContent>
    </Card>
  );
}
