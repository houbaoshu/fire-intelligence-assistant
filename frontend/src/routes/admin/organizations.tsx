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
import { Textarea } from "@/components/ui/textarea";
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
import { formatDateTime } from "@/lib/datetime";
import { adminService, type AdminOrganization } from "@/lib/services/admin";

export const Route = createFileRoute("/admin/organizations")({
  head: () => ({
    meta: [
      { title: "组织管理 · 消防智能助手" },
      { name: "description", content: "管理平台组织:新建、编辑与删除。" },
    ],
  }),
  component: AdminOrganizationsPage,
});

const PAGE_SIZE = 20;

function AdminOrganizationsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<AdminOrganization | null>(null);
  const [deleting, setDeleting] = useState<AdminOrganization | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin", "organizations", page],
    queryFn: ({ signal }) => adminService.listOrganizations({ page, page_size: PAGE_SIZE }, signal),
    enabled: isAdmin,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "organizations"] });

  const saveMutation = useMutation({
    mutationFn: (form: { name: string; code: string; description: string }) => {
      const description = form.description.trim() || undefined;
      return editing
        ? adminService.updateOrganization(editing.id, {
            name: form.name.trim(),
            code: form.code.trim(),
            description,
          })
        : adminService.createOrganization({
            name: form.name.trim(),
            code: form.code.trim(),
            description,
          });
    },
    onSuccess: () => {
      toast.success(editing ? "组织已更新" : "组织已创建");
      setDialogOpen(false);
      setEditing(null);
      invalidate();
    },
    onError: (e) => toast.error(`保存失败:${readableAdminError(e, "请稍后重试")}`),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminService.deleteOrganization(id),
    onSuccess: () => {
      toast.success("组织已删除");
      setDeleting(null);
      invalidate();
    },
    // 409(仍有用户归属)等冲突:保留确认框并在框内展示后端可读错误。
    onError: (e) => toast.error(`删除失败:${readableAdminError(e, "请稍后重试")}`),
  });

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-5xl">
        <PageHeader title="组织管理" />
        <AdminAccessDenied />
      </div>
    );
  }

  const data = listQuery.data;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="组织管理"
        description="管理平台内的组织(租户)。删除前须先迁移其归属用户。"
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" /> 新建组织
          </Button>
        }
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm">组织列表</CardTitle>
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
            <EmptyState title="暂无组织" description="点击右上角「新建组织」创建第一个组织。" />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>编码</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="w-24" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((org) => (
                    <TableRow key={org.id}>
                      <TableCell className="font-medium">{org.name}</TableCell>
                      <TableCell className="font-mono text-muted-foreground">{org.code}</TableCell>
                      <TableCell className="max-w-64 truncate text-muted-foreground">
                        {org.description ?? "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(org.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => {
                              setEditing(org);
                              setDialogOpen(true);
                            }}
                            aria-label={`编辑 ${org.name}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setDeleting(org)}
                            aria-label={`删除 ${org.name}`}
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

      <OrganizationFormDialog
        open={dialogOpen}
        editing={editing}
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
            <AlertDialogTitle>确认删除组织?</AlertDialogTitle>
            <AlertDialogDescription>
              将删除「{deleting?.name}
              」。若仍有用户归属该组织,后端将拒绝删除并返回原因。此操作不可撤销。
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

function OrganizationFormDialog({
  open,
  editing,
  isPending,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  editing: AdminOrganization | null;
  isPending: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (form: { name: string; code: string; description: string }) => void;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  // 打开对话框时按编辑对象初始化表单(渲染期派生,避免 effect 级联)。
  const formKey = open ? (editing?.id ?? "new") : null;
  if (formKey && formKey !== loadedFor) {
    setLoadedFor(formKey);
    setName(editing?.name ?? "");
    setCode(editing?.code ?? "");
    setDescription(editing?.description ?? "");
  }

  const valid = name.trim().length > 0 && code.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? "编辑组织" : "新建组织"}</DialogTitle>
          <DialogDescription>编码为组织唯一标识,保存后仍可修改但须保持唯一。</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="org-name">名称</Label>
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如:某市消防救援支队"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="org-code">编码</Label>
            <Input
              id="org-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="例如:xf-zd-001"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="org-description">描述(可选)</Label>
            <Textarea
              id="org-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            取消
          </Button>
          <Button
            onClick={() => onSubmit({ name, code, description })}
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
