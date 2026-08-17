import { CheckCheck, Stamp } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { RecordStatus } from "@/lib/services/common";

export type RecordStatusActionsProps = {
  status: RecordStatus;
  /** 有未保存更改时禁用状态流转,先保存。 */
  dirty: boolean;
  pending: boolean;
  /** 定稿前的额外校验信息(如拍照报告须至少选中一张图片);非空时禁用定稿并展示。 */
  finalizeBlocker?: string | null;
  onMarkReviewed: () => void;
  onFinalize: () => void;
};

/**
 * 记录状态流转操作(UX 层):标记已审阅 / 定稿。
 * 授权以后端校验为准,403 / 409 由调用方展示可读错误。
 */
export function RecordStatusActions({
  status,
  dirty,
  pending,
  finalizeBlocker,
  onMarkReviewed,
  onFinalize,
}: RecordStatusActionsProps) {
  const canReview = status === "draft" || status === "generated";
  const canFinalize = status === "reviewed";
  const finalized = status === "finalized" || status === "archived";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        size="sm"
        variant="outline"
        disabled={!canReview || dirty || pending}
        onClick={onMarkReviewed}
      >
        <CheckCheck className="mr-2 h-4 w-4" /> 标记为已审阅
      </Button>
      <Button
        size="sm"
        disabled={!canFinalize || dirty || pending || !!finalizeBlocker}
        onClick={onFinalize}
      >
        <Stamp className="mr-2 h-4 w-4" /> 定稿
      </Button>
      {dirty && <span className="text-xs text-muted-foreground">请先保存更改再变更状态</span>}
      {!dirty && finalizeBlocker && status !== "finalized" && status !== "archived" && (
        <span className="text-xs text-muted-foreground">{finalizeBlocker}</span>
      )}
      {finalized && (
        <span className="text-xs text-muted-foreground">
          记录已{status === "finalized" ? "定稿" : "归档"};修改冲突将由后端拒绝(409)
        </span>
      )}
    </div>
  );
}
