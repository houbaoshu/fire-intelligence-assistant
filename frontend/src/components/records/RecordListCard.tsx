import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { RECORD_STATUSES, type Paginated, type RecordStatus } from "@/lib/services/common";
import { RECORD_STATUS_LABELS } from "@/lib/labels";

const ALL = "__all__";

export type RecordListColumn<T> = {
  header: ReactNode;
  render: (item: T) => ReactNode;
  className?: string;
};

export type RecordListCardProps<T> = {
  title: string;
  status: RecordStatus | undefined;
  onStatusChange: (status: RecordStatus | undefined) => void;
  page: number;
  onPageChange: (page: number) => void;
  data: Paginated<T> | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  columns: RecordListColumn<T>[];
  getKey: (item: T) => string;
  onOpen: (item: T) => void;
  emptyDescription?: string;
};

/** 业务记录列表区块:状态过滤、分页、loading / empty / error 三态。 */
export function RecordListCard<T>({
  title,
  status,
  onStatusChange,
  page,
  onPageChange,
  data,
  isLoading,
  error,
  onRetry,
  columns,
  getKey,
  onOpen,
  emptyDescription = "提交生成任务后,记录将出现在这里。",
}: RecordListCardProps<T>) {
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle className="text-sm">{title}</CardTitle>
        <Select
          value={status ?? ALL}
          onValueChange={(v) => onStatusChange(v === ALL ? undefined : (v as RecordStatus))}
        >
          <SelectTrigger className="h-8 w-32" aria-label="按状态过滤">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>全部状态</SelectItem>
            {RECORD_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {RECORD_STATUS_LABELS[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState
            description={error instanceof Error ? error.message : "加载失败"}
            onRetry={onRetry}
          />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="暂无记录" description={emptyDescription} />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((c, i) => (
                    <TableHead key={i} className={c.className}>
                      {c.header}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((item) => (
                  <TableRow
                    key={getKey(item)}
                    className="cursor-pointer"
                    onClick={() => onOpen(item)}
                  >
                    {columns.map((c, i) => (
                      <TableCell key={i} className={c.className}>
                        {c.render(item)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
              <span>
                共 {data.total} 条 · 第 {data.page} / {totalPages} 页
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
          </>
        )}
      </CardContent>
    </Card>
  );
}
