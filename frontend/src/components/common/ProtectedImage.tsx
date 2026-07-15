import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { photoReportService } from "@/lib/services/photo-report";

export function ProtectedImage({
  reportId,
  imageId,
  alt,
}: {
  reportId: string;
  imageId: string;
  alt: string;
}) {
  const query = useQuery({
    queryKey: ["photo-preview", reportId, imageId],
    queryFn: ({ signal }) => photoReportService.preview(reportId, imageId, signal),
    staleTime: 5 * 60 * 1000,
  });
  const url = useMemo(() => (query.data ? URL.createObjectURL(query.data) : null), [query.data]);
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );

  if (query.isLoading) {
    return (
      <div className="aspect-video animate-pulse rounded-md bg-muted" aria-label="图片加载中" />
    );
  }
  if (!url) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-md bg-muted text-xs text-muted-foreground">
        图片不可用
      </div>
    );
  }
  return <img src={url} alt={alt} className="aspect-video w-full rounded-md object-cover" />;
}
