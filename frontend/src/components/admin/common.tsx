import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/common/StateViews";

/** /admin 路由区共享的展示件:分页页脚与非管理员访问提示。 */

/** 非 admin 直接访问 /admin/* 时的提示(不发起请求,避免无意义的 403)。 */
export function AdminAccessDenied() {
  return (
    <ErrorState
      title="仅管理员可访问"
      description="系统管理功能仅对 admin 角色开放。如需访问,请联系管理员调整角色。"
    />
  );
}

/** 分页页脚:与 knowledge-base 等既有列表页一致的模式。 */
export function ListPagination({
  page,
  total,
  pageSize,
  onPageChange,
}: {
  page: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
      <span>
        共 {total} 条 · 第 {page} / {totalPages} 页
      </span>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="mr-1 h-3.5 w-3.5" /> 上一页
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          下一页 <ChevronRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
