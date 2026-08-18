import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import {
  LayoutDashboard,
  MessageSquareText,
  ClipboardList,
  Images,
  Mic,
  BookOpen,
  ListChecks,
  Settings as SettingsIcon,
  Flame,
  LogOut,
  Building2,
  FolderTree,
  Users,
  ShieldCheck,
  ScrollText,
  FileText,
  Cpu,
  FlaskConical,
  Puzzle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { BackendStatusBadge } from "@/components/common/BackendStatus";
import { LoadingState } from "@/components/common/StateViews";
import { NotificationBell } from "@/components/common/NotificationBell";
import { Button } from "@/components/ui/button";

/** 公开页面：不渲染应用外壳与业务导航。 */
const PUBLIC_PATHS = new Set(["/login", "/register"]);

type NavItem = { to: string; label: string; icon: ReactNode };

const NAV: NavItem[] = [
  { to: "/", label: "工作台", icon: <LayoutDashboard className="h-4 w-4" /> },
  { to: "/regulation-qa", label: "法规问答", icon: <MessageSquareText className="h-4 w-4" /> },
  { to: "/inspection-record", label: "检查记录", icon: <ClipboardList className="h-4 w-4" /> },
  { to: "/photo-report", label: "图像报告", icon: <Images className="h-4 w-4" /> },
  { to: "/interview-record", label: "询问笔录", icon: <Mic className="h-4 w-4" /> },
  { to: "/knowledge-base", label: "知识库", icon: <BookOpen className="h-4 w-4" /> },
  { to: "/tasks", label: "任务中心", icon: <ListChecks className="h-4 w-4" /> },
  { to: "/settings", label: "设置", icon: <SettingsIcon className="h-4 w-4" /> },
];

/** 系统管理分组:仅 admin 角色可见(纯 UX;授权由后端逐次校验,403 按其错误信封展示)。 */
const ADMIN_NAV: NavItem[] = [
  { to: "/admin/organizations", label: "组织管理", icon: <Building2 className="h-4 w-4" /> },
  { to: "/admin/departments", label: "部门管理", icon: <FolderTree className="h-4 w-4" /> },
  { to: "/admin/users", label: "用户管理", icon: <Users className="h-4 w-4" /> },
  { to: "/admin/permissions", label: "权限管理", icon: <ShieldCheck className="h-4 w-4" /> },
  { to: "/admin/audit-logs", label: "审计日志", icon: <ScrollText className="h-4 w-4" /> },
  { to: "/admin/prompts", label: "Prompt 管理", icon: <FileText className="h-4 w-4" /> },
  { to: "/admin/models", label: "模型配置", icon: <Cpu className="h-4 w-4" /> },
  { to: "/admin/evaluations", label: "评估运行", icon: <FlaskConical className="h-4 w-4" /> },
  { to: "/admin/plugins", label: "插件管理", icon: <Puzzle className="h-4 w-4" /> },
];

export function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user, isInitializing, isAuthenticated, logout } = useAuth();

  // 登录 / 注册为独立公开页，不渲染应用外壳。
  if (PUBLIC_PATHS.has(pathname)) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <Outlet />
      </div>
    );
  }

  // 会话初始化完成前不渲染受保护内容，避免闪现；
  // 未认证时 __root 的 beforeLoad 会跳转登录页，此处仅作兜底占位。
  if (isInitializing || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <LoadingState title="正在验证登录状态…" className="w-full max-w-md" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-sidebar text-sidebar-foreground md:flex md:flex-col">
        <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Flame className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">消防智能助手</div>
            <div className="text-[10px] text-muted-foreground">Fire Intelligence</div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV.map((item) => (
            <NavLink key={item.to} item={item} pathname={pathname} />
          ))}
          {user?.role === "admin" && (
            <>
              <div className="px-3 pb-1 pt-4 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                系统管理
              </div>
              {ADMIN_NAV.map((item) => (
                <NavLink key={item.to} item={item} pathname={pathname} />
              ))}
            </>
          )}
        </nav>
        <div className="border-t border-sidebar-border p-3">
          <div className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium">{user?.full_name || user?.email}</div>
              {user?.full_name && (
                <div className="truncate text-[10px] text-muted-foreground">{user.email}</div>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              title="退出登录"
              aria-label="退出登录"
              className="h-8 w-8 shrink-0"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-2 text-[10px] text-muted-foreground">v0.1 · Frontend Foundation</div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-card/50 px-4 backdrop-blur">
          <MobileNav pathname={pathname} />
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-xs text-muted-foreground sm:inline">
              {user?.full_name || user?.email}
            </span>
            <NotificationBell />
            <BackendStatusBadge compact />
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              title="退出登录"
              aria-label="退出登录"
              className="h-8 w-8 md:hidden"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
  return (
    <Link
      to={item.to}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition",
        "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        active && "bg-sidebar-accent text-sidebar-accent-foreground font-medium",
      )}
    >
      {item.icon}
      <span>{item.label}</span>
    </Link>
  );
}

function MobileNav({ pathname }: { pathname: string }) {
  const { user } = useAuth();
  const items = user?.role === "admin" ? [...NAV, ...ADMIN_NAV] : NAV;
  return (
    <div className="flex items-center gap-1 overflow-x-auto md:hidden">
      {items.map((item) => {
        const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
        return (
          <Link
            key={item.to}
            to={item.to}
            className={cn(
              "flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-1 text-xs",
              active ? "bg-accent text-accent-foreground" : "text-muted-foreground",
            )}
          >
            {item.icon}
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
