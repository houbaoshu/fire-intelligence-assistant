import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw, Save } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { AdminAccessDenied } from "@/components/admin/common";
import { readableAdminError } from "@/lib/admin-error";
import { useAuth } from "@/hooks/useAuth";
import { USER_ROLE_LABELS } from "@/lib/labels";
import { USER_ROLES, type UserRole } from "@/lib/services/auth";
import { adminService } from "@/lib/services/admin";

export const Route = createFileRoute("/admin/permissions")({
  head: () => ({
    meta: [
      { title: "权限管理 · 消防智能助手" },
      { name: "description", content: "编辑各角色的权限码矩阵;admin 的 admin.* 权限不可变更。" },
    ],
  }),
  component: AdminPermissionsPage,
});

type MatrixState = Record<UserRole, Set<string>>;

function toMatrixState(matrix: Partial<Record<UserRole, string[]>>): MatrixState {
  return {
    admin: new Set(matrix.admin ?? []),
    supervisor: new Set(matrix.supervisor ?? []),
    inspector: new Set(matrix.inspector ?? []),
    viewer: new Set(matrix.viewer ?? []),
  };
}

function setsEqual(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}

/** admin 角色的 admin.* 权限禁止编辑(后端同样会拒绝),避免管理员自锁。 */
function isLockedCell(role: UserRole, code: string): boolean {
  return role === "admin" && code.startsWith("admin.");
}

function AdminPermissionsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [draft, setDraft] = useState<MatrixState | null>(null);
  const [baseline, setBaseline] = useState<MatrixState | null>(null);
  const [loaded, setLoaded] = useState(false);

  const matrixQuery = useQuery({
    queryKey: ["admin", "permissions"],
    queryFn: ({ signal }) => adminService.getPermissions(signal),
    enabled: isAdmin,
  });

  // 数据首次到达时初始化草稿与基线(渲染期派生,避免 effect 级联)。
  const matrixData = matrixQuery.data;
  if (matrixData && !loaded) {
    setLoaded(true);
    const state = toMatrixState(matrixData.matrix);
    setDraft(state);
    setBaseline(state);
  }

  const dirtyRoles = USER_ROLES.filter(
    (r) => draft && baseline && !setsEqual(draft[r], baseline[r]),
  );

  const saveMutation = useMutation({
    // 逐角色覆盖式提交;任一失败即中止并展示后端可读错误。
    mutationFn: async (roles: UserRole[]) => {
      for (const role of roles) {
        await adminService.updateRolePermissions(role, [...(draft?.[role] ?? [])].sort());
      }
      return roles;
    },
    onSuccess: (roles) => {
      toast.success(`已保存 ${roles.length} 个角色的权限`);
      qc.invalidateQueries({ queryKey: ["admin", "permissions"] });
      setLoaded(false);
    },
    onError: (e) => toast.error(`保存失败:${readableAdminError(e, "请稍后重试")}`),
  });

  const toggle = (role: UserRole, code: string, checked: boolean) => {
    if (isLockedCell(role, code)) return;
    setDraft((prev) => {
      if (!prev) return prev;
      const next: MatrixState = { ...prev, [role]: new Set(prev[role]) };
      if (checked) next[role].add(code);
      else next[role].delete(code);
      return next;
    });
  };

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader title="权限管理" />
        <AdminAccessDenied />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="权限管理"
        description="按角色勾选授予的权限码。保存时仅提交有变更的角色;admin 的 admin.* 权限锁定不可编辑。"
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => matrixQuery.refetch()}
              disabled={matrixQuery.isFetching}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${matrixQuery.isFetching ? "animate-spin" : ""}`}
              />
              刷新
            </Button>
            <Button
              onClick={() => saveMutation.mutate(dirtyRoles)}
              disabled={dirtyRoles.length === 0 || saveMutation.isPending}
            >
              {saveMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              {saveMutation.isPending
                ? "保存中…"
                : dirtyRoles.length > 0
                  ? `保存变更(${dirtyRoles.length})`
                  : "保存变更"}
            </Button>
          </>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">权限矩阵</CardTitle>
        </CardHeader>
        <CardContent>
          {matrixQuery.isLoading ? (
            <LoadingState />
          ) : matrixQuery.error ? (
            <ErrorState
              description={readableAdminError(matrixQuery.error, "加载失败")}
              onRetry={() => {
                setLoaded(false);
                matrixQuery.refetch();
              }}
            />
          ) : !matrixData || matrixData.permissions.length === 0 ? (
            <EmptyState title="暂无权限定义" description="后端尚未返回任何权限码。" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-64">权限</TableHead>
                  {USER_ROLES.map((r) => (
                    <TableHead key={r} className="text-center">
                      {USER_ROLE_LABELS[r]}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {matrixData.permissions.map((p) => (
                  <TableRow key={p.code}>
                    <TableCell>
                      <div className="font-mono text-xs text-foreground">{p.code}</div>
                      <div className="text-sm font-medium">{p.name}</div>
                      {p.description && (
                        <div className="text-xs text-muted-foreground">{p.description}</div>
                      )}
                    </TableCell>
                    {USER_ROLES.map((r) => {
                      const locked = isLockedCell(r, p.code);
                      return (
                        <TableCell key={r} className="text-center">
                          <Checkbox
                            checked={draft?.[r].has(p.code) ?? false}
                            disabled={locked || saveMutation.isPending}
                            onCheckedChange={(v) => toggle(r, p.code, v === true)}
                            aria-label={`${USER_ROLE_LABELS[r]} · ${p.code}`}
                            title={locked ? "admin 的 admin.* 权限不可编辑" : undefined}
                          />
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
