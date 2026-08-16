import { createFileRoute, Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Eye, EyeOff, Loader2, Lock, Mail } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api-client";
import { ErrorState } from "@/components/common/StateViews";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "登录 · 消防智能助手" },
      { name: "description", content: "登录消防智能助手。" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const routerState = useRouterState();
  const search = routerState.location.search as Record<string, unknown>;
  const redirectTo = typeof search.redirect === "string" ? search.redirect : "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // already authenticated -> go to the app
  if (status === "authenticated") {
    void navigate({ to: redirectTo as never, replace: true });
  }

  const canSubmit = email.trim().length > 0 && password.length > 0 && !submitting;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      await navigate({ to: redirectTo as never, replace: true });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "登录失败,请稍后重试";
      setError(message);
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center">
      <PageHeader title="登录" description="使用您的账号登录消防智能助手。" />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">账号登录</CardTitle>
          <CardDescription>邮箱与密码</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                  placeholder="user@example.com"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 pr-9"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? "隐藏密码" : "显示密码"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={!canSubmit}>
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              登录
            </Button>
          </form>

          <div className="mt-4 text-center text-sm text-muted-foreground">
            还没有账号?
            <Link to="/register" className="ml-1 font-medium text-primary hover:underline">
              注册
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
