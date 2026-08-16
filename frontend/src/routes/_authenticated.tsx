import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/hooks/useAuth";

export const Route = createFileRoute("/_authenticated")({
  component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
  const { status } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (status === "anonymous") {
      // preserve the intended destination for post-login restore
      void navigate({
        to: "/login",
        search: { redirect: window.location.pathname },
        replace: true,
      });
    }
  }, [status, navigate]);

  if (status === "loading" || status === "anonymous") {
    // never flash protected content before the session resolves
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">
        <div className="flex items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>正在验证会话…</span>
        </div>
      </div>
    );
  }

  return <AppShell />;
}
