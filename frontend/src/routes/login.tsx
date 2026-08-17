import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Flame, Loader2 } from "lucide-react";
import { authService } from "@/lib/services/auth";
import { authErrorMessage, safeRedirectTarget } from "@/lib/auth-utils";
import { PasswordInput } from "@/components/auth/PasswordInput";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type LoginSearch = { redirect?: string };

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "登录 · 消防智能助手" },
      { name: "description", content: "使用邮箱与密码登录消防智能助手。" },
    ],
  }),
  component: LoginPage,
});

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function LoginPage() {
  const { redirect: redirectTarget } = Route.useSearch();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  const loginMutation = useMutation({
    mutationFn: () => authService.login(email.trim(), password),
    onSuccess: (user) => {
      // 写入当前用户，避免受保护路由守卫再次请求 me。
      queryClient.setQueryData(["auth", "me"], user);
      router.history.push(safeRedirectTarget(redirectTarget));
    },
  });
  const pending = loginMutation.isPending;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (pending) return;
    const errors: { email?: string; password?: string } = {};
    const normalizedEmail = email.trim();
    if (!normalizedEmail) errors.email = "请输入邮箱";
    else if (!EMAIL_RE.test(normalizedEmail)) errors.email = "邮箱格式不正确";
    if (!password) errors.password = "请输入密码";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    loginMutation.mutate(undefined, {
      // 登录失败：保留 email，清空 password。
      onError: () => setPassword(""),
    });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Flame className="h-5 w-5" />
          </div>
          <CardTitle>登录消防智能助手</CardTitle>
          <CardDescription>使用邮箱与密码登录以继续使用平台</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (fieldErrors.email) setFieldErrors((prev) => ({ ...prev, email: undefined }));
                }}
                disabled={pending}
                aria-invalid={!!fieldErrors.email}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
              />
              {fieldErrors.email && (
                <p id="email-error" className="text-xs text-destructive">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">密码</Label>
              <PasswordInput
                id="password"
                value={password}
                onChange={(v) => {
                  setPassword(v);
                  if (fieldErrors.password)
                    setFieldErrors((prev) => ({ ...prev, password: undefined }));
                }}
                disabled={pending}
                invalid={!!fieldErrors.password}
                describedBy={fieldErrors.password ? "password-error" : undefined}
              />
              {fieldErrors.password && (
                <p id="password-error" className="text-xs text-destructive">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {loginMutation.isError && (
              <div
                role="alert"
                className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {authErrorMessage(loginMutation.error)}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={pending}>
              {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {pending ? "正在登录…" : "登录"}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              还没有账号？
              <Link
                to="/register"
                search={{ redirect: redirectTarget }}
                className="text-primary hover:underline"
              >
                注册
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
