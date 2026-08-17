import { Link } from "@tanstack/react-router";
import type { Task } from "@/lib/services/tasks";
import { cn } from "@/lib/utils";

/**
 * 已完成任务 → 关联业务记录的安全导航链接(specs/workflow.md §5/§6)。
 * 生成类任务按 task_type 映射到对应记录详情(record_id 取自 result_data,
 * 不向用户暴露原始 result_data);knowledge_* 类型链接到知识库;
 * 映射不到或未完成的任务不渲染链接。
 */
export function TaskRecordLink({ task, className }: { task: Task; className?: string }) {
  if (task.status !== "completed") return null;
  const cls = cn("text-xs text-primary hover:underline", className);
  const recordId = task.result_data?.record_id;
  switch (task.task_type) {
    case "inspection_record_generation":
      return recordId ? (
        <Link className={cls} to="/inspection-record/$id" params={{ id: recordId }}>
          查看记录
        </Link>
      ) : null;
    case "photo_report_generation":
      return recordId ? (
        <Link className={cls} to="/photo-report/$id" params={{ id: recordId }}>
          查看报告
        </Link>
      ) : null;
    case "interview_record_generation":
      return recordId ? (
        <Link className={cls} to="/interview-record/$id" params={{ id: recordId }}>
          查看笔录
        </Link>
      ) : null;
    case "knowledge_indexing":
    case "knowledge_reindexing":
      return (
        <Link className={cls} to="/knowledge-base">
          查看知识库
        </Link>
      );
    default:
      return null;
  }
}
