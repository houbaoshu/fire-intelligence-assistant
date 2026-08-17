import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { GenerateSection } from "@/components/records/GenerateSection";
import { RecordListCard } from "@/components/records/RecordListCard";
import { RecordStatusBadge } from "@/components/common/StatusBadges";
import {
  inspectionRecordService,
  type InspectionRecordListItem,
} from "@/lib/services/inspection-record";
import type { RecordStatus } from "@/lib/services/common";
import { formatDateTime } from "@/lib/datetime";
import { loadPreferences } from "@/lib/preferences";

export const Route = createFileRoute("/inspection-record/")({
  head: () => ({
    meta: [
      { title: "检查记录 · 消防智能助手" },
      { name: "description", content: "上传检查视频,生成结构化检查记录草稿并导出 Word。" },
    ],
  }),
  component: InspectionRecordListPage,
});

const VIDEO_MAX_SIZE = 500 * 1024 * 1024;

function InspectionRecordListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<RecordStatus | undefined>(undefined);
  const pageSize = loadPreferences().pageSize;

  const listQuery = useQuery({
    queryKey: ["inspection-record", "list", { page, pageSize, status }],
    queryFn: ({ signal }) =>
      inspectionRecordService.list({ page, page_size: pageSize, status }, signal),
  });

  const openDetail = (id: string) => navigate({ to: "/inspection-record/$id", params: { id } });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="检查记录"
        description="上传一段现场检查视频与可选备注,提交后由后端异步生成结构化草稿;下方为已有记录列表。"
      />

      <GenerateSection
        storageKey="inspection-record"
        fileField="video"
        cardTitle="上传视频生成检查记录"
        accept="video/mp4,video/quicktime,.mp4,.mov"
        maxSize={VIDEO_MAX_SIZE}
        hint="仅支持 mp4 / mov,单个文件,不超过 500MB"
        remarksPlaceholder="填写检查地点、现场情况等补充信息"
        generate={(fd) => inspectionRecordService.generate(fd)}
        onRecordReady={openDetail}
      />

      <RecordListCard<InspectionRecordListItem>
        title="记录列表"
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
            header: "记录编号",
            render: (item) => (
              <span className="font-mono text-xs">{item.record_number ?? "—"}</span>
            ),
          },
          {
            header: "标题",
            render: (item) => item.title ?? <span className="text-muted-foreground">未命名</span>,
          },
          {
            header: "被检查单位",
            render: (item) => item.inspection_unit ?? "—",
            className: "hidden md:table-cell",
          },
          {
            header: "检查日期",
            render: (item) => formatDateTime(item.inspection_date),
            className: "hidden lg:table-cell",
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
