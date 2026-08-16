/** Record status labels shared across record pages. */
export const RECORD_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  processing: "生成中",
  generated: "已生成",
  reviewed: "已审阅",
  finalized: "已定稿",
  archived: "已归档",
  failed: "失败",
};

export const RECORD_STATUS_TONES: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  processing: "bg-blue-500/15 text-blue-600",
  generated: "bg-amber-500/15 text-amber-700",
  reviewed: "bg-violet-500/15 text-violet-700",
  finalized: "bg-emerald-500/15 text-emerald-700",
  archived: "bg-muted text-muted-foreground",
  failed: "bg-destructive/15 text-destructive",
};

export const ITEM_TYPE_LABELS: Record<string, string> = {
  compliant: "符合",
  violation: "违规",
  hazard: "隐患",
  observation: "观察项",
  recommendation: "建议",
};

export const SEVERITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  critical: "严重",
};
