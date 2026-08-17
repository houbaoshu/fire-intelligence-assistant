import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import { adminService, type AdminDepartment, type AdminOrganization } from "@/lib/services/admin";

export const Route = createFileRoute("/admin/departments")({
  head: () => ({
    meta: [
      { title: "部门管理 · 消防智能助手" },
      { name: "description", content: "按组织管理部门层级:新建、编辑与删除。" },
    ],
  }),
  component: AdminDepartmentsPage,
});

const PAGE_SIZE = 20;
/** 下拉选项用列表上限(组织 / 部门选项不做分页交互)。 */
const OPTIONS_PAGE_SIZE = 100;
const ALL = "__all__";
const NONE = "__none__";

function AdminDepartmentsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [orgFilter, setOrgFilter] = useState<string | undefined>(undefined);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<AdminDepartment | null>(null);
  const [deleting, setDeleting] = useState<AdminDepartment | null>(null);

  const orgsQuery = useQuery({
    queryKey: ["admin", "organizations", "options"],
    queryFn: ({ signal }) =>
      adminService.listOrganizations({ page: 1, page_size: OPTIONS_PAGE_SIZE }, signal),
    enabled: isAdmin,
  });

  const listQuery = useQuery({
    queryKey: ["admin", "departments", page, orgFilter],
    queryFn: ({ signal }) =>
      adminService.listDepartments(
        { page, page_size: PAGE_SIZE, organization_id: orgFilter },
        signal,
      ),
    enabled: isAdmin,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "departments"] });

  const saveMutation = useMutation({
    mutationFn: (form: { organizationId: string; name: string; parentId: string | null }) =>
      editing
        ? adminService.updateDepartment(editing.id, {
            name: form.name.trim(),
            parent_id: form.parentId,
          })
        : adminService.createDepartment({
            organization_id: form.organizationId,
            name: form.name.trim(),
            parent_id: form.parentId ?? undefined,
          }),
    onSuccess: () => {
      toast.success(editing ? "部门已更新" : "部门已创建");
      setDialogOpen(false);
      setEditing(null);
      invalidate();
    },
    onError: (e) => toast.error(`保存失败:${readableAdminError(e, "请稍后重试")}`),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminService.deleteDepartment(id),
    onSuccess: () => {
      toast.success("部门已删除");
      setDeleting(null);
      invalidate();
    },
    onError: (e) => toast.error(`删除失败:${readableAdminError(e, "请稍后重试")}`),
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-5xl">
        <PageHeader title="部门管理" />
        <AdminAccessDenied />
      </div>
    );
  }

  const data = listQuery.data;
  const orgs = orgsQuery.data?.items ?? [];
  const orgName = (id: string) => orgs.find((o) => o.id === id)?.name ?? id;
  const deptName = (id: string | null) =>
    id ? (data?.items.find((d) => d.id === id)?.name ?? id) : "—";

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="部门管理"
        description="按组织维护部门层级。删除有子部门或归属用户的部门可能被后端拒绝。"
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" /> 新建部门
          </Button>
        }
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">部门列表</CardTitle>
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
              title="暂无部门"
              description={
                orgFilter
                  ? "该组织下还没有部门,可切换组织过滤查看。"
                  : "点击右上角「新建部门」创建第一个部门。"
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>所属组织</TableHead>
                    <TableHead>上级部门</TableHead>
                    <TableHead className="w-24" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="font-medium">{d.name}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {orgName(d.organization_id)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {deptName(d.parent_id)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => {
                              setEditing(d);
                              setDialogOpen(true);
                            }}
                            aria-label={`编辑 ${d.name}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setDeleting(d)}
                            aria-label={`删除 ${d.name}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
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

      <DepartmentFormDialog
        open={dialogOpen}
        editing={editing}
        organizations={orgs}
        isPending={saveMutation.isPending}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditing(null);
        }}
        onSubmit={(form) => saveMutation.mutate(form)}
      />

      <AlertDialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除部门?</AlertDialogTitle>
            <AlertDialogDescription>
              将删除「{deleting?.name}
              」。若该部门仍有子部门或归属用户,后端将拒绝删除并返回原因。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteMutation.error && (
            <p className="text-sm text-destructive">
              {readableAdminError(deleteMutation.error, "删除失败,请稍后重试")}
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>取消</AlertDialogCancel>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
            >
              {deleteMutation.isPending ? "删除中…" : "确认删除"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function DepartmentFormDialog({
  open,
  editing,
  organizations,
  isPending,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  editing: AdminDepartment | null;
  organizations: AdminOrganization[];
  isPending: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (form: { organizationId: string; name: string; parentId: string | null }) => void;
}) {
  const [organizationId, setOrganizationId] = useState("");
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState<string | null>(null);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  // 打开对话框时按编辑对象初始化表单(渲染期派生,避免 effect 级联)。
  const formKey = open ? (editing?.id ?? "new") : null;
  if (formKey && formKey !== loadedFor) {
    setLoadedFor(formKey);
    setOrganizationId(editing?.organization_id ?? "");
    setName(editing?.name ?? "");
    setParentId(editing?.parent_id ?? null);
  }

  // 上级部门选项:同组织内的其他部门(编辑时排除自身,避免自引用)。
  const parentsQuery = useQuery({
    queryKey: ["admin", "departments", "options", organizationId],
    queryFn: ({ signal }) =>
      adminService.listDepartments(
        { page: 1, page_size: OPTIONS_PAGE_SIZE, organization_id: organizationId },
        signal,
      ),
    enabled: open && organizationId.length > 0,
  });
  const parentOptions = (parentsQuery.data?.items ?? []).filter((d) => d.id !== editing?.id);

  const valid = name.trim().length > 0 && organizationId.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? "编辑部门" : "新建部门"}</DialogTitle>
          <DialogDescription>
            {editing ? "所属组织不可变更;如需调整请新建部门。" : "选择所属组织,上级部门可选。"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>所属组织</Label>
            <Select
              value={organizationId}
              onValueChange={(v) => {
                setOrganizationId(v);
                setParentId(null);
              }}
              disabled={editing !== null}
            >
              <SelectTrigger aria-label="所属组织">
                <SelectValue placeholder="选择组织" />
              </SelectTrigger>
              <SelectContent>
                {organizations.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="dept-name">名称</Label>
            <Input
              id="dept-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如:防火监督处"
            />
          </div>
          <div className="space-y-2">
            <Label>上级部门(可选)</Label>
            <Select
              value={parentId ?? NONE}
              onValueChange={(v) => setParentId(v === NONE ? null : v)}
              disabled={!organizationId}
            >
              <SelectTrigger aria-label="上级部门">
                <SelectValue placeholder="无上级部门" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>无上级部门</SelectItem>
                {parentOptions.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            取消
          </Button>
          <Button
            onClick={() => onSubmit({ organizationId, name, parentId })}
            disabled={!valid || isPending}
          >
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isPending ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
