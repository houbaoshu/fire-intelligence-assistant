import { Badge } from "@/components/ui/badge";
import {
  KNOWLEDGE_STATUS_LABELS,
  RECORD_STATUS_LABELS,
  TASK_STATUS_LABELS,
  labelOf,
} from "@/lib/labels";
import type { RecordStatus } from "@/lib/services/common";
import type { KnowledgeDocumentStatus } from "@/lib/services/knowledge";
import type { TaskStatus } from "@/lib/services/tasks";
import { cn } from "@/lib/utils";

const RECORD_TONES: Partial<Record<RecordStatus, string>> = {
  finalized: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  reviewed: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-400",
  failed: "border-destructive/40 bg-destructive/10 text-destructive",
  archived: "border-border bg-muted text-muted-foreground",
  processing: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
};

/** 业务记录状态徽章;未知状态回退展示原始值。 */
export function RecordStatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("whitespace-nowrap", RECORD_TONES[status as RecordStatus])}
    >
      {labelOf(RECORD_STATUS_LABELS, status)}
    </Badge>
  );
}

const TASK_TONES: Partial<Record<TaskStatus, string>> = {
  completed: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  failed: "border-destructive/40 bg-destructive/10 text-destructive",
  processing: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  cancelled: "border-border bg-muted text-muted-foreground",
};

/** 任务状态徽章;未知状态回退展示原始值(specs/dashboard.md:中性兜底)。 */
export function TaskStatusBadge({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={cn("whitespace-nowrap", TASK_TONES[status as TaskStatus])}>
      {labelOf(TASK_STATUS_LABELS, status)}
    </Badge>
  );
}

const KNOWLEDGE_TONES: Partial<Record<KnowledgeDocumentStatus, string>> = {
  indexed: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  failed: "border-destructive/40 bg-destructive/10 text-destructive",
  parsing: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  indexing: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  outdated: "border-border bg-muted text-muted-foreground",
};

/** 知识库文档索引状态徽章;状态同时以文字表达,不依赖颜色(specs/knowledge-base.md)。 */
export function KnowledgeStatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("whitespace-nowrap", KNOWLEDGE_TONES[status as KnowledgeDocumentStatus])}
    >
      {labelOf(KNOWLEDGE_STATUS_LABELS, status)}
    </Badge>
  );
}
