import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { USER_ROLE_LABELS } from "@/lib/labels";
import { USER_ROLES, type UserRole } from "@/lib/services/auth";
import { adminService, type AdminUser, type UserUpdateBody } from "@/lib/services/admin";

export const Route = createFileRoute("/admin/users")({
  head: () => ({
    meta: [
      { title: "用户管理 · 消防智能助手" },
      { name: "description", content: "管理平台用户:角色、启用状态与组织/部门归属。" },
    ],
  }),
  component: AdminUsersPage,
});

const PAGE_SIZE = 20;
const OPTIONS_PAGE_SIZE = 100;
const ALL = "__all__";

function AdminUsersPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [orgFilter, setOrgFilter] = useState<string | undefined>(undefined);
  const [roleFilter, setRoleFilter] = useState<UserRole | undefined>(undefined);
  const [editing, setEditing] = useState<AdminUser | null>(null);

  // 组织 / 部门名称映射(列表只返回 id);选项级数据不分页。
  const orgsQuery = useQuery({
    queryKey: ["admin", "organizations", "options"],
    queryFn: ({ signal }) =>
      adminService.listOrganizations({ page: 1, page_size: OPTIONS_PAGE_SIZE }, signal),
    enabled: isAdmin,
  });
  const deptsQuery = useQuery({
    queryKey: ["admin", "departments", "options"],
    queryFn: ({ signal }) =>
      adminService.listDepartments({ page: 1, page_size: OPTIONS_PAGE_SIZE }, signal),
    enabled: isAdmin,
  });

  const listQuery = useQuery({
    queryKey: ["admin", "users", page, orgFilter, roleFilter],
    queryFn: ({ signal }) =>
      adminService.listUsers(
        { page, page_size: PAGE_SIZE, organization_id: orgFilter, role: roleFilter },
        signal,
      ),
    enabled: isAdmin,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserUpdateBody }) =>
      adminService.updateUser(id, body),
    onSuccess: () => {
      toast.success("用户已更新");
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    // 409(自锁保护)等冲突:保留对话框,错误在框内展示。
    onError: (e) => toast.error(`保存失败:${readableAdminError(e, "请稍后重试")}`),
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader title="用户管理" />
        <AdminAccessDenied />
      </div>
    );
  }

  const data = listQuery.data;
  const orgs = orgsQuery.data?.items ?? [];
  const depts = deptsQuery.data?.items ?? [];
  const orgName = (id: string | null) => (id ? (orgs.find((o) => o.id === id)?.name ?? "—") : "—");
  const deptName = (id: string | null) =>
    id ? (depts.find((d) => d.id === id)?.name ?? "—") : "—";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader title="用户管理" description="调整用户角色、启用状态与组织/部门归属。" />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">用户列表</CardTitle>
          <div className="flex items-center gap-2">
            <Select
              value={orgFilter ?? ALL}
              onValueChange={(v) => {
                setOrgFilter(v === ALL ? undefined : v);
                setPage(1);
              }}
            >
              <SelectTrigger className="h-8 w-44" aria-label="按组织过滤">
                <SelectValue placeholder="全部组织" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>全部组织</SelectItem>
                {orgs.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={roleFilter ?? ALL}
              onValueChange={(v) => {
                setRoleFilter(v === ALL ? undefined : (v as UserRole));
                setPage(1);
              }}
            >
              <SelectTrigger className="h-8 w-32" aria-label="按角色过滤">
                <SelectValue placeholder="全部角色" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>全部角色</SelectItem>
                {USER_ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {USER_ROLE_LABELS[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
              title="暂无用户"
              description={
                orgFilter || roleFilter ? "当前过滤条件下没有用户,可调整过滤条件。" : undefined
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>邮箱</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>组织</TableHead>
                    <TableHead>部门</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>最近登录</TableHead>
                    <TableHead className="w-12" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell className="font-medium">{u.email}</TableCell>
                      <TableCell className="text-muted-foreground">{u.full_name}</TableCell>
                      <TableCell>
                        <Badge variant={u.role === "admin" ? "default" : "secondary"}>
                          {USER_ROLE_LABELS[u.role] ?? u.role}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {orgName(u.organization_id)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {deptName(u.department_id)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={u.is_active ? "outline" : "destructive"}>
                          {u.is_active ? "启用" : "停用"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(u.last_login_at)}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => setEditing(u)}
                          aria-label={`编辑 ${u.email}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
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

      <UserEditDialog
        user={editing}
        organizations={orgs}
        isPending={updateMutation.isPending}
        error={updateMutation.error}
        onOpenChange={(open) => {
          if (!open) {
            setEditing(null);
            updateMutation.reset();
          }
        }}
        onSubmit={(body) => editing && updateMutation.mutate({ id: editing.id, body })}
      />
    </div>
  );
}

const NONE = "__none__";

function UserEditDialog({
  user,
  organizations,
  isPending,
  error,
  onOpenChange,
  onSubmit,
}: {
  user: AdminUser | null;
  organizations: { id: string; name: string }[];
  isPending: boolean;
  error: Error | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (body: {
    role: UserRole;
    is_active: boolean;
    organization_id: string | null;
    department_id: string | null;
  }) => void;
}) {
  const [role, setRole] = useState<UserRole>("viewer");
  const [isActive, setIsActive] = useState(true);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [departmentId, setDepartmentId] = useState<string | null>(null);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  // 打开对话框时按目标用户初始化表单(渲染期派生,避免 effect 级联)。
  if (user && user.id !== loadedFor) {
    setLoadedFor(user.id);
    setRole(user.role);
    setIsActive(user.is_active);
    setOrganizationId(user.organization_id);
    setDepartmentId(user.department_id);
  }

  // 部门选项随所选组织联动过滤;切换组织时清空已选部门。
  const deptsQuery = useQuery({
    queryKey: ["admin", "departments", "options", organizationId ?? NONE],
    queryFn: ({ signal }) =>
      adminService.listDepartments(
        { page: 1, page_size: OPTIONS_PAGE_SIZE, organization_id: organizationId ?? undefined },
        signal,
      ),
    enabled: user !== null && organizationId !== null,
  });
  const deptOptions = deptsQuery.data?.items ?? [];

  return (
    <Dialog open={user !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>编辑用户</DialogTitle>
          <DialogDescription>{user?.email}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>角色</Label>
            <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
              <SelectTrigger aria-label="角色">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {USER_ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {USER_ROLE_LABELS[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="user-active">启用状态</Label>
              <p className="text-xs text-muted-foreground">停用后该用户无法登录平台。</p>
            </div>
            <Switch id="user-active" checked={isActive} onCheckedChange={setIsActive} />
          </div>
          <div className="space-y-2">
            <Label>所属组织</Label>
            <Select
              value={organizationId ?? NONE}
              onValueChange={(v) => {
                setOrganizationId(v === NONE ? null : v);
                setDepartmentId(null);
              }}
            >
              <SelectTrigger aria-label="所属组织">
                <SelectValue placeholder="未分配" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>未分配</SelectItem>
                {organizations.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>所属部门</Label>
            <Select
              value={departmentId ?? NONE}
              onValueChange={(v) => setDepartmentId(v === NONE ? null : v)}
              disabled={organizationId === null}
            >
              <SelectTrigger aria-label="所属部门">
                <SelectValue placeholder="未分配" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>未分配</SelectItem>
                {deptOptions.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        {error && (
          <p className="text-sm text-destructive">
            {readableAdminError(error, "保存失败,请稍后重试")}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            取消
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                role,
                is_active: isActive,
                organization_id: organizationId,
                department_id: departmentId,
              })
            }
            disabled={isPending}
          >
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isPending ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
