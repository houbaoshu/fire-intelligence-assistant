/**
 * 枚举值的中文展示标签。枚举取值定义权在 docs/DATABASE.md,
 * 此处仅维护 UI 文案;未知值一律回退为原始值展示。
 */
import type { RecordStatus } from "./services/common";
import type { InspectionItemType, InspectionSeverity } from "./services/inspection-record";
import type { TaskStatus, TaskType } from "./services/tasks";
import type { StatisticsScope } from "./services/statistics";
import type { KnowledgeDocumentStatus } from "./services/knowledge";

export const RECORD_STATUS_LABELS: Record<RecordStatus, string> = {
  draft: "草稿",
  processing: "生成中",
  generated: "已生成",
  reviewed: "已审阅",
  finalized: "已定稿",
  archived: "已归档",
  failed: "失败",
};

export const ITEM_TYPE_LABELS: Record<InspectionItemType, string> = {
  compliant: "合规项",
  violation: "违规",
  hazard: "隐患",
  observation: "观察项",
  recommendation: "建议",
};

export const SEVERITY_LABELS: Record<InspectionSeverity, string> = {
  low: "低",
  medium: "中",
  high: "高",
  critical: "严重",
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "等待中",
  queued: "已排队",
  processing: "处理中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  inspection_record_generation: "检查记录生成",
  photo_report_generation: "拍照报告生成",
  interview_record_generation: "询问记录生成",
  speech_transcription: "语音转写",
  video_analysis: "视频分析",
  document_generation: "文书生成",
  knowledge_indexing: "知识库索引",
  knowledge_reindexing: "知识库重建索引",
};

export const SCOPE_LABELS: Record<StatisticsScope, string> = {
  personal: "个人",
  team: "团队",
  organization: "组织",
  system: "全系统",
};

export const KNOWLEDGE_STATUS_LABELS: Record<KnowledgeDocumentStatus, string> = {
  uploaded: "已上传",
  parsing: "解析中",
  indexing: "索引中",
  indexed: "已索引",
  failed: "失败",
  outdated: "已失效",
};

export function labelOf(map: Record<string, string>, value: string | null | undefined): string {
  if (!value) return "—";
  return map[value] ?? value;
}
