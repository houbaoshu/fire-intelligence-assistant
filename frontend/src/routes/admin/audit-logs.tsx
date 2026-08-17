import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, RefreshCw, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { AdminAccessDenied, ListPagination } from "@/components/admin/common";
import { readableAdminError } from "@/lib/admin-error";
import { useAuth } from "@/hooks/useAuth";
import { formatDateTime } from "@/lib/datetime";
import { adminService, type AdminAuditLog } from "@/lib/services/admin";

export const Route = createFileRoute("/admin/audit-logs")({
  head: () => ({
    meta: [
      { title: "审计日志 · 消防智能助手" },
      { name: "description", content: "查看管理操作审计日志,支持按操作与实体类型过滤。" },
    ],
  }),
  component: AdminAuditLogsPage,
});

const PAGE_SIZE = 20;

function summarizeDetails(details: Record<string, unknown> | null): string {
  if (!details) return "—";
  const keys = Object.keys(details);
  if (keys.length === 0) return "—";
  return `${keys.length} 个字段:${keys.slice(0, 3).join("、")}${keys.length > 3 ? "…" : ""}`;
}

function AdminAuditLogsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [page, setPage] = useState(1);
  // 输入草稿与已生效过滤条件分离,点击「查询」后才发起请求,避免逐键请求。
  const [actionInput, setActionInput] = useState("");
  const [entityTypeInput, setEntityTypeInput] = useState("");
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined);
  const [entityTypeFilter, setEntityTypeFilter] = useState<string | undefined>(undefined);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin", "audit-logs", page, actionFilter, entityTypeFilter],
    queryFn: ({ signal }) =>
      adminService.listAuditLogs(
        { page, page_size: PAGE_SIZE, action: actionFilter, entity_type: entityTypeFilter },
        signal,
      ),
    enabled: isAdmin,
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader title="审计日志" />
        <AdminAccessDenied />
      </div>
    );
  }

  const data = listQuery.data;

  const applyFilters = () => {
    setActionFilter(actionInput.trim() || undefined);
    setEntityTypeFilter(entityTypeInput.trim() || undefined);
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader title="审计日志" description="系统管理操作的审计记录,只读。" />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">日志列表</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={actionInput}
              onChange={(e) => setActionInput(e.target.value)}
              placeholder="按操作过滤,如 user.update"
              className="h-8 w-48"
              aria-label="按操作过滤"
              onKeyDown={(e) => e.key === "Enter" && applyFilters()}
            />
            <Input
              value={entityTypeInput}
              onChange={(e) => setEntityTypeInput(e.target.value)}
              placeholder="按实体类型过滤,如 user"
              className="h-8 w-44"
              aria-label="按实体类型过滤"
              onKeyDown={(e) => e.key === "Enter" && applyFilters()}
            />
            <Button size="sm" variant="outline" onClick={applyFilters}>
              <Search className="mr-2 h-3.5 w-3.5" /> 查询
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => listQuery.refetch()}
              disabled={listQuery.isFetching}
            >
              <RefreshCw
                className={`mr-2 h-3.5 w-3.5 ${listQuery.isFetching ? "animate-spin" : ""}`}
              />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.error ? (
            <ErrorState
              description={readableAdminError(listQuery.error, "加载失败")}
              onRetry={() => listQuery.refetch()}
            />
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              title="暂无审计日志"
              description={
                actionFilter || entityTypeFilter
                  ? "当前过滤条件下没有日志,可调整过滤条件。"
                  : "执行管理操作后将在此生成审计记录。"
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>用户</TableHead>
                    <TableHead>操作</TableHead>
                    <TableHead>实体</TableHead>
                    <TableHead>IP</TableHead>
                    <TableHead>详情</TableHead>
                    <TableHead className="w-12" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((log) => (
                    <AuditLogRow
                      key={log.id}
                      log={log}
                      expanded={expandedId === log.id}
                      onToggle={() => setExpandedId(expandedId === log.id ? null : log.id)}
                    />
                  ))}
                </TableBody>
              </Table>
              <ListPagination
                page={data.page}
                total={data.total}
                pageSize={data.page_size}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function AuditLogRow({
  log,
  expanded,
  onToggle,
}: {
  log: AdminAuditLog;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <TableRow>
        <TableCell className="whitespace-nowrap text-muted-foreground">
          {formatDateTime(log.created_at)}
        </TableCell>
        <TableCell className="max-w-40 truncate font-mono text-xs">{log.user_id ?? "—"}</TableCell>
        <TableCell className="font-mono text-xs">{log.action}</TableCell>
        <TableCell className="text-muted-foreground">
          {log.entity_type
            ? `${log.entity_type}${log.entity_id ? ` / ${log.entity_id}` : ""}`
            : "—"}
        </TableCell>
        <TableCell className="font-mono text-xs text-muted-foreground">
          {log.ip_address ?? "—"}
        </TableCell>
        <TableCell className="text-xs text-muted-foreground">
          {summarizeDetails(log.details)}
        </TableCell>
        <TableCell>
          {log.details && (
            <Button
              size="icon"
              variant="ghost"
              onClick={onToggle}
              aria-label={expanded ? "收起详情" : "展开详情"}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          )}
        </TableCell>
      </TableRow>
      {expanded && log.details && (
        <TableRow>
          <TableCell colSpan={7} className="bg-muted/40">
            <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
