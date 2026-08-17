import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { GenerateSection } from "@/components/records/GenerateSection";
import { RecordListCard } from "@/components/records/RecordListCard";
import { RecordStatusBadge } from "@/components/common/StatusBadges";
import { photoReportService, type PhotoReportListItem } from "@/lib/services/photo-report";
import type { RecordStatus } from "@/lib/services/common";
import { formatDateTime } from "@/lib/datetime";
import { loadPreferences } from "@/lib/preferences";

export const Route = createFileRoute("/photo-report/")({
  head: () => ({
    meta: [
      { title: "图像报告 · 消防智能助手" },
      { name: "description", content: "上传检查视频,由后端抽取关键帧生成图像报告草稿。" },
    ],
  }),
  component: PhotoReportListPage,
});

const VIDEO_MAX_SIZE = 500 * 1024 * 1024;

function PhotoReportListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<RecordStatus | undefined>(undefined);
  const pageSize = loadPreferences().pageSize;

  const listQuery = useQuery({
    queryKey: ["photo-report", "list", { page, pageSize, status }],
    queryFn: ({ signal }) => photoReportService.list({ page, page_size: pageSize, status }, signal),
  });

  const openDetail = (id: string) => navigate({ to: "/photo-report/$id", params: { id } });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="图像报告"
        description="上传检查视频,后端将抽取关键帧并识别地址、违规描述,供审阅编辑;下方为已有报告列表。"
      />

      <GenerateSection
        storageKey="photo-report"
        fileField="video"
        cardTitle="上传视频生成拍照报告"
        accept="video/mp4,video/quicktime,.mp4,.mov"
        maxSize={VIDEO_MAX_SIZE}
        hint="仅支持 mp4 / mov,单个文件,不超过 500MB"
        remarksPlaceholder="填写检查地点、现场情况等补充信息"
        generate={(fd) => photoReportService.generate(fd)}
        onRecordReady={openDetail}
      />

      <RecordListCard<PhotoReportListItem>
        title="报告列表"
        status={status}
        onStatusChange={(s) => {
          setStatus(s);
          setPage(1);
        }}
        page={page}
        onPageChange={setPage}
        data={listQuery.data}
        isLoading={listQuery.isLoading}
        error={listQuery.error}
        onRetry={() => listQuery.refetch()}
        getKey={(item) => item.id}
        onOpen={(item) => openDetail(item.id)}
        columns={[
          {
            header: "标题",
            render: (item) => item.title ?? <span className="text-muted-foreground">未命名</span>,
          },
          {
            header: "被检查单位",
            render: (item) => item.inspection_unit ?? "—",
            className: "hidden md:table-cell",
          },
          { header: "状态", render: (item) => <RecordStatusBadge status={item.status} /> },
          {
            header: "创建时间",
            render: (item) => formatDateTime(item.created_at),
            className: "hidden md:table-cell",
          },
        ]}
      />
    </div>
  );
}
