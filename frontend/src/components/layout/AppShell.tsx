import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import {
  LayoutDashboard,
  MessageSquareText,
  ClipboardList,
  Images,
  Mic,
  BookOpen,
  Settings as SettingsIcon,
  Flame,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BackendStatusBadge } from "@/components/common/BackendStatus";

type NavItem = { to: string; label: string; icon: ReactNode };

const NAV: NavItem[] = [
  { to: "/", label: "工作台", icon: <LayoutDashboard className="h-4 w-4" /> },
  { to: "/regulation-qa", label: "法规问答", icon: <MessageSquareText className="h-4 w-4" /> },
  { to: "/inspection-record", label: "检查记录", icon: <ClipboardList className="h-4 w-4" /> },
  { to: "/photo-report", label: "图像报告", icon: <Images className="h-4 w-4" /> },
  { to: "/interview-record", label: "询问笔录", icon: <Mic className="h-4 w-4" /> },
  { to: "/knowledge-base", label: "知识库", icon: <BookOpen className="h-4 w-4" /> },
  { to: "/settings", label: "设置", icon: <SettingsIcon className="h-4 w-4" /> },
];

export function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

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
        <nav className="flex-1 space-y-0.5 p-2">
          {NAV.map((item) => {
            const active =
              item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition",
                  "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  active &&
                    "bg-sidebar-accent text-sidebar-accent-foreground font-medium",
                )}
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-sidebar-border p-3 text-[10px] text-muted-foreground">
          v0.1 · Frontend Foundation
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-card/50 px-4 backdrop-blur">
          <MobileNav pathname={pathname} />
          <div className="ml-auto">
            <BackendStatusBadge compact />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function MobileNav({ pathname }: { pathname: string }) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto md:hidden">
      {NAV.map((item) => {
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
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
