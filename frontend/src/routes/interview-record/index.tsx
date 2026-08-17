import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/AppShell";
import { GenerateSection } from "@/components/records/GenerateSection";
import { RecordListCard } from "@/components/records/RecordListCard";
import { RecordStatusBadge } from "@/components/common/StatusBadges";
import {
  interviewRecordService,
  type InterviewRecordListItem,
} from "@/lib/services/interview-record";
import type { RecordStatus } from "@/lib/services/common";
import { formatDateTime } from "@/lib/datetime";
import { loadPreferences } from "@/lib/preferences";

export const Route = createFileRoute("/interview-record/")({
  head: () => ({
    meta: [
      { title: "询问笔录 · 消防智能助手" },
      { name: "description", content: "上传询问录音,生成转写原文与结构化询问笔录草稿。" },
    ],
  }),
  component: InterviewRecordListPage,
});

const AUDIO_MAX_SIZE = 200 * 1024 * 1024;

function InterviewRecordListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<RecordStatus | undefined>(undefined);
  const pageSize = loadPreferences().pageSize;

  const listQuery = useQuery({
    queryKey: ["interview-record", "list", { page, pageSize, status }],
    queryFn: ({ signal }) =>
      interviewRecordService.list({ page, page_size: pageSize, status }, signal),
  });

  const openDetail = (id: string) => navigate({ to: "/interview-record/$id", params: { id } });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="询问笔录"
        description="上传询问录音(v1 仅支持音频),后端将转写并生成结构化笔录草稿;下方为已有记录列表。"
      />

      <GenerateSection
        storageKey="interview-record"
        fileField="audio"
        cardTitle="上传录音生成询问笔录"
        accept="audio/wav,audio/mpeg,audio/mp4,.wav,.mp3,.m4a"
        maxSize={AUDIO_MAX_SIZE}
        hint="仅支持 wav / mp3 / m4a,单个文件,不超过 200MB"
        remarksPlaceholder="填写询问背景、被询问人身份等补充信息"
        generate={(fd) => interviewRecordService.generate(fd)}
        onRecordReady={openDetail}
      />

      <RecordListCard<InterviewRecordListItem>
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
            header: "标题",
            render: (item) => item.title ?? <span className="text-muted-foreground">未命名</span>,
          },
          {
            header: "被询问人",
            render: (item) => item.interviewee_name ?? "—",
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
