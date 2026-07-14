import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertCircle, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthPage } from "@/features/auth/AuthPage";
import { useAuth } from "@/features/auth/auth-context";
import { ApiError } from "@/lib/api-client";
import { authService } from "@/lib/services/auth";

type LoginSearch = { redirect?: string };

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  head: () => ({ meta: [{ title: "登录 · 消防智能助手" }] }),
  component: LoginPage,
});

function LoginPage() {
  const { redirect } = Route.useSearch();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const config = useQuery({
    queryKey: ["auth-config"],
    queryFn: ({ signal }) => authService.config(signal),
    staleTime: 60_000,
    retry: 0,
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      window.location.replace(safeRedirect(redirect));
    } catch (caught) {
      setPassword("");
      setError(authErrorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPage title="登录" description="使用您的账号进入消防检查工作平台。">
      <form className="space-y-4" onSubmit={handleSubmit}>
        {error && (
          <Alert variant="destructive" aria-live="polite">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="space-y-2">
          <Label htmlFor="email">邮箱</Label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            disabled={submitting}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">密码</Label>
          <div className="relative">
            <Input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="pr-10"
              required
              disabled={submitting}
            />
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
              aria-label={showPassword ? "隐藏密码" : "显示密码"}
              disabled={submitting}
            >
              {showPassword ? <EyeOff /> : <Eye />}
            </button>
          </div>
        </div>
        <Button className="w-full" type="submit" disabled={submitting}>
          {submitting && <LoaderCircle className="animate-spin" />}
          {submitting ? "正在登录…" : "登录"}
        </Button>
        {config.data?.registration_enabled && (
          <p className="text-center text-sm text-muted-foreground">
            还没有账号？
            <Link to="/register" className="ml-1 text-foreground underline underline-offset-4">
              注册
            </Link>
          </p>
        )}
      </form>
    </AuthPage>
  );
}

function safeRedirect(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  if (value.startsWith("/login") || value.startsWith("/register")) return "/";
  return value;
}

function authErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "INVALID_CREDENTIALS") return "邮箱或密码不正确。";
    if (error.code === "NETWORK_ERROR" || error.code === "API_BASE_URL_MISSING") {
      return "暂时无法连接后端服务，请检查连接后重试。";
    }
  }
  return "登录失败，请稍后重试。";
}
