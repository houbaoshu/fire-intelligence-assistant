import { Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { LoaderCircle } from "lucide-react";
import { useEffect } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/features/auth/auth-context";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AuthBoundary() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useRouterState({ select: (state) => state.location });
  const isPublic = PUBLIC_PATHS.has(location.pathname);

  useEffect(() => {
    if (auth.status === "unauthenticated" && !isPublic) {
      void navigate({
        to: "/login",
        search: { redirect: `${location.pathname}${location.searchStr}` },
        replace: true,
      });
    } else if (auth.status === "authenticated" && isPublic) {
      void navigate({ to: "/", replace: true });
    }
  }, [auth.status, isPublic, location.pathname, location.searchStr, navigate]);

  if (isPublic) return <Outlet />;
  if (auth.status !== "authenticated") return <FullPageLoader />;
  return <AppShell />;
}

function FullPageLoader() {
  return (
    <div
      className="flex min-h-screen items-center justify-center gap-2 bg-background text-sm text-muted-foreground"
      role="status"
    >
      <LoaderCircle className="h-4 w-4 animate-spin" />
      正在验证登录状态…
    </div>
  );
}
