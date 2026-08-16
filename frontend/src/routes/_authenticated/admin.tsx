import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  Users as UsersIcon,
  Building2,
  ScrollText,
} from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { api } from "@/lib/api-client";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({
    meta: [
      { title: "系统管理 · 消防智能助手" },
      { name: "description", content: "用户、组织与审计日志管理。" },
    ],
  }),
  component: AdminPage,
});

type AdminUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  organization_id: string | null;
  department_id: string | null;
  created_at: string;
};

const ROLE_LABELS: Record<string, string> = {
  admin: "管理员",
  supervisor: "主管",
  inspector: "检查员",
  viewer: "访客",
};

function AdminPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"users" | "orgs" | "audit">("users");

  if (user?.role !== "admin") {
    return (
      <div className="mx-auto max-w-3xl">
        <PageHeader
          title="系统管理"
          description="仅管理员可访问。"
          actions={
            <Button variant="outline" onClick={() => navigate({ to: "/" })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> 返回工作台
            </Button>
          }
        />
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            您没有系统管理权限。如需管理用户、组织或查看审计日志,请联系管理员。
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="系统管理" description="用户与组织管理、审计日志查看。" />
      <div className="mb-4 flex gap-2">
        <TabButton
          active={tab === "users"}
          onClick={() => setTab("users")}
          icon={<UsersIcon className="h-4 w-4" />}
          label="用户管理"
        />
        <TabButton
          active={tab === "orgs"}
          onClick={() => setTab("orgs")}
          icon={<Building2 className="h-4 w-4" />}
          label="组织与部门"
        />
        <TabButton
          active={tab === "audit"}
          onClick={() => setTab("audit")}
          icon={<ScrollText className="h-4 w-4" />}
          label="审计日志"
        />
      </div>
      {tab === "users" && <UsersTab />}
      {tab === "orgs" && <OrgsTab />}
      {tab === "audit" && <AuditTab />}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition " +
        (active
          ? "bg-primary text-primary-foreground"
          : "bg-card text-muted-foreground hover:bg-accent")
      }
    >
      {icon}
      {label}
    </button>
  );
}

function UsersTab() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["admin-users"],
    queryFn: ({ signal }) =>
      api.get<{ items: AdminUser[]; total: number }>("/api/admin/users?page=1&page_size=100", {
        signal,
      }),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      api.put("/api/admin/users/" + encodeURIComponent(id), { role }),
    onSuccess: () => {
      toast.success("角色已更新");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error("更新失败:" + e.message),
  });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">用户列表</CardTitle>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")} />
          刷新
        </Button>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <LoadingState description="正在加载用户…" />
        ) : query.isError ? (
          <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
        ) : (
          <div className="divide-y">
            {query.data?.items.map((u) => (
              <div key={u.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {u.full_name || u.email}
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {ROLE_LABELS[u.role] ?? u.role}
                    </span>
                    {!u.is_active && <span className="text-xs text-destructive">已停用</span>}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {u.email} · 创建于 {new Date(u.created_at).toLocaleDateString("zh-CN")}
                  </div>
                </div>
                <select
                  value={u.role}
                  onChange={(e) => roleMutation.mutate({ id: u.id, role: e.target.value })}
                  className="rounded-md border border-input bg-background px-2 py-1 text-sm"
                  disabled={roleMutation.isPending}
                >
                  {Object.entries(ROLE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

type OrgItem = { id: string; name: string; code: string; description: string | null };
type DeptItem = { id: string; organization_id: string; name: string };

function OrgsTab() {
  const qc = useQueryClient();
  const orgsQuery = useQuery({
    queryKey: ["admin-orgs"],
    queryFn: ({ signal }) => api.get<{ items: OrgItem[] }>("/api/admin/organizations", { signal }),
  });
  const deptsQuery = useQuery({
    queryKey: ["admin-depts"],
    queryFn: ({ signal }) => api.get<{ items: DeptItem[] }>("/api/admin/departments", { signal }),
  });
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [deptOrg, setDeptOrg] = useState("");
  const [deptName, setDeptName] = useState("");

  const createOrg = useMutation({
    mutationFn: () => api.post("/api/admin/organizations", { name, code }),
    onSuccess: () => {
      toast.success("组织已创建");
      setName("");
      setCode("");
      qc.invalidateQueries({ queryKey: ["admin-orgs"] });
    },
    onError: (e) => toast.error("创建失败:" + e.message),
  });

  const createDept = useMutation({
    mutationFn: () =>
      api.post("/api/admin/departments", { organization_id: deptOrg, name: deptName }),
    onSuccess: () => {
      toast.success("部门已创建");
      setDeptName("");
      qc.invalidateQueries({ queryKey: ["admin-depts"] });
    },
    onError: (e) => toast.error("创建失败:" + e.message),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">组织列表</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">组织名称</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="消防支队"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">组织编码</Label>
              <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="FIRE-01" />
            </div>
          </div>
          <Button
            onClick={() => createOrg.mutate()}
            disabled={!name || !code || createOrg.isPending}
          >
            创建组织
          </Button>
          <div className="divide-y">
            {orgsQuery.data?.items.map((o) => (
              <div key={o.id} className="flex items-center justify-between py-2 text-sm">
                <span className="font-medium">{o.name}</span>
                <span className="font-mono text-xs text-muted-foreground">{o.code}</span>
              </div>
            ))}
            {orgsQuery.data && orgsQuery.data.items.length === 0 && (
              <div className="py-4 text-center text-sm text-muted-foreground">暂无组织</div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">部门管理</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">所属组织</Label>
              <select
                value={deptOrg}
                onChange={(e) => setDeptOrg(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
              >
                <option value="">选择组织</option>
                {orgsQuery.data?.items.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">部门名称</Label>
              <Input
                value={deptName}
                onChange={(e) => setDeptName(e.target.value)}
                placeholder="监督科"
              />
            </div>
          </div>
          <Button
            onClick={() => createDept.mutate()}
            disabled={!deptOrg || !deptName || createDept.isPending}
          >
            创建部门
          </Button>
          <div className="divide-y">
            {deptsQuery.data?.items.map((d) => (
              <div key={d.id} className="py-2 text-sm">
                {d.name}
                <span className="ml-2 text-xs text-muted-foreground">
                  {orgsQuery.data?.items.find((o) => o.id === d.organization_id)?.name ??
                    "未知组织"}
                </span>
              </div>
            ))}
            {deptsQuery.data && deptsQuery.data.items.length === 0 && (
              <div className="py-4 text-center text-sm text-muted-foreground">暂无部门</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

type AuditItem = {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
};

function AuditTab() {
  const query = useQuery({
    queryKey: ["admin-audit"],
    queryFn: ({ signal }) =>
      api.get<{ items: AuditItem[]; total: number }>("/api/admin/audit-logs?page=1&page_size=100", {
        signal,
      }),
  });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">审计日志(仅追加)</CardTitle>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")} />
          刷新
        </Button>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <LoadingState description="正在加载日志…" />
        ) : query.isError ? (
          <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
        ) : query.data && query.data.items.length === 0 ? (
          <EmptyState title="暂无审计日志" />
        ) : (
          <div className="divide-y">
            {query.data?.items.map((a) => (
              <div key={a.id} className="py-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono text-xs">{a.action}</span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(a.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  用户 {a.user_id ? a.user_id.slice(0, 8) : "系统"}
                  {a.entity_type ? " · " + a.entity_type : ""}
                  {a.ip_address ? " · " + a.ip_address : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
