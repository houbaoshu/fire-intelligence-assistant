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

export const Route = createFileRoute("/register")({
  head: () => ({ meta: [{ title: "注册 · 消防智能助手" }] }),
  component: RegisterPage,
});

function RegisterPage() {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
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
      await register(email, password, username);
      window.location.replace("/");
    } catch (caught) {
      setPassword("");
      setError(registrationErrorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  if (config.data && !config.data.registration_enabled) {
    return (
      <AuthPage title="注册已关闭" description="当前环境不允许自行注册账号。">
        <Button asChild className="w-full">
          <Link to="/login">返回登录</Link>
        </Button>
      </AuthPage>
    );
  }

  return (
    <AuthPage title="创建账号" description="注册后将以检查员身份进入平台。">
      <form className="space-y-4" onSubmit={handleSubmit}>
        {error && (
          <Alert variant="destructive" aria-live="polite">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="space-y-2">
          <Label htmlFor="username">姓名或显示名称</Label>
          <Input
            id="username"
            name="username"
            autoComplete="name"
            minLength={2}
            maxLength={100}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={submitting}
          />
        </div>
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
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="pr-10"
              required
              disabled={submitting}
              aria-describedby="password-help"
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
          <p id="password-help" className="text-xs text-muted-foreground">
            至少 12 个字符。请勿使用其他系统的相同密码。
          </p>
        </div>
        <Button className="w-full" type="submit" disabled={submitting}>
          {submitting && <LoaderCircle className="animate-spin" />}
          {submitting ? "正在创建账号…" : "注册并登录"}
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          已有账号？
          <Link to="/login" className="ml-1 text-foreground underline underline-offset-4">
            返回登录
          </Link>
        </p>
      </form>
    </AuthPage>
  );
}

function registrationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "EMAIL_ALREADY_REGISTERED") return "该邮箱已注册，请直接登录。";
    if (error.code === "REGISTRATION_DISABLED") return "当前环境已关闭账号注册。";
    if (error.code === "VALIDATION_ERROR") return "请检查邮箱、显示名称和密码是否符合要求。";
    if (error.code === "NETWORK_ERROR" || error.code === "API_BASE_URL_MISSING") {
      return "暂时无法连接后端服务，请检查连接后重试。";
    }
  }
  return "注册失败，请稍后重试。";
}
