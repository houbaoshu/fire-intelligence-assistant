/**
 * 枚举值的中文展示标签。枚举取值定义权在 docs/DATABASE.md,
 * 此处仅维护 UI 文案;未知值一律回退为原始值展示。
 */
import type { RecordStatus } from "./services/common";
import type { UserRole } from "./services/auth";
import type { InspectionItemType, InspectionSeverity } from "./services/inspection-record";
import type { TaskStatus, TaskType } from "./services/tasks";
import type { StatisticsScope } from "./services/statistics";
import type { KnowledgeDocumentStatus } from "./services/knowledge";
import type { ModelKind } from "./services/ai-platform";

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

/**
 * 任务阶段(current_stage)的中文标签。阶段名是后端写入的稳定机器值
 * (backend/app/services/pipelines/* 与 rag/indexing.py),此处仅做 UI 本地化;
 * 未知值由 labelOf 回退为原始值展示。
 */
export const TASK_STAGE_LABELS: Record<string, string> = {
  video_analysis: "视频分析",
  frame_extraction: "视频抽帧",
  frame_dedup: "关键帧去重",
  vision_analysis: "图像理解",
  speech_transcription: "语音转写",
  transcript_cleanup: "转写整理",
  speaker_diarization: "说话人分离",
  ocr: "文字识别",
  evidence_normalization: "证据归一化",
  llm_extract: "内容抽取",
  draft: "草稿生成",
  parsing: "文档解析",
  chunking: "文档分块",
  embedding: "向量化",
  vector_index: "向量索引",
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

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  admin: "管理员",
  supervisor: "主管",
  inspector: "检查员",
  viewer: "只读用户",
};

/** 模型能力类型(docs/DATABASE.md model_configurations.kind)的中文标签。 */
export const MODEL_KIND_LABELS: Record<ModelKind, string> = {
  llm: "大语言模型",
  vision: "视觉",
  ocr: "OCR",
  speech: "语音识别",
  embedding: "Embedding",
  reranker: "Reranker",
};

/**
 * 评估运行状态的中文标签。状态机取值定义权在后端(evaluation_results.status),
 * 此处仅做 UI 本地化;未知值由 labelOf 回退为原始值展示。
 */
export const EVALUATION_STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  failed: "失败",
};

export function labelOf(map: Record<string, string>, value: string | null | undefined): string {
  if (!value) return "—";
  return map[value] ?? value;
}
