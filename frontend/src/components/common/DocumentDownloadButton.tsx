import { useMutation } from "@tanstack/react-query";
import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { downloadBlob } from "@/lib/download";

export type DocumentDownloadButtonProps = {
  /** 经 api-client 获取文件流(携带 Authorization)。 */
  fetchBlob: () => Promise<Blob>;
  /** 下载文件名,按 API.md §4 约定生成。 */
  filename: string;
  disabled?: boolean;
};

/**
 * 文书下载按钮:调用后端 download 端点获取 blob 并触发浏览器下载。
 * 409(文档未生成)等错误展示后端返回的可读 message。
 */
export function DocumentDownloadButton({
  fetchBlob,
  filename,
  disabled,
}: DocumentDownloadButtonProps) {
  const mutation = useMutation({
    mutationFn: async () => {
      const blob = await fetchBlob();
      downloadBlob(blob, filename);
    },
  });

  const error = mutation.error;
  const hint =
    error instanceof ApiError && error.status === 409
      ? `文书尚未生成:${error.message}`
      : error instanceof Error
        ? error.message
        : null;

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <Button
        variant="outline"
        size="sm"
        onClick={() => mutation.mutate()}
        disabled={disabled || mutation.isPending}
      >
        {mutation.isPending ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Download className="mr-2 h-4 w-4" />
        )}
        下载文书
      </Button>
      {hint && <div className="max-w-xs text-xs text-destructive">{hint}</div>}
    </div>
  );
}
