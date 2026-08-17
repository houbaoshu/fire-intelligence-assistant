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

type RegisterSearch = { redirect?: string };

export const Route = createFileRoute("/register")({
  validateSearch: (search: Record<string, unknown>): RegisterSearch => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "注册 · 消防智能助手" },
      { name: "description", content: "注册消防智能助手账号。" },
    ],
  }),
  component: RegisterPage,
});

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type FieldErrors = { fullName?: string; email?: string; password?: string };

function RegisterPage() {
  const { redirect: redirectTarget } = Route.useSearch();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const registerMutation = useMutation({
    mutationFn: () => authService.register(email.trim(), password, fullName.trim()),
    onSuccess: (user) => {
      // 注册响应直接返回令牌，按登录成功处理。
      queryClient.setQueryData(["auth", "me"], user);
      router.history.push(safeRedirectTarget(redirectTarget));
    },
  });
  const pending = registerMutation.isPending;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (pending) return;
    const errors: FieldErrors = {};
    if (!fullName.trim()) errors.fullName = "请输入姓名";
    const normalizedEmail = email.trim();
    if (!normalizedEmail) errors.email = "请输入邮箱";
    else if (!EMAIL_RE.test(normalizedEmail)) errors.email = "邮箱格式不正确";
    // 密码强度策略以后端为准，此处仅做即时反馈。
    if (!password) errors.password = "请输入密码";
    else if (password.length < 8) errors.password = "密码至少 8 位";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    registerMutation.mutate(undefined, {
      // 注册失败：保留 email 与姓名，清空 password。
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
          <CardTitle>注册账号</CardTitle>
          <CardDescription>注册是否开放由后端决定；注册成功后将直接登录</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="full-name">姓名</Label>
              <Input
                id="full-name"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => {
                  setFullName(e.target.value);
                  if (fieldErrors.fullName)
                    setFieldErrors((prev) => ({ ...prev, fullName: undefined }));
                }}
                disabled={pending}
                aria-invalid={!!fieldErrors.fullName}
                aria-describedby={fieldErrors.fullName ? "full-name-error" : undefined}
              />
              {fieldErrors.fullName && (
                <p id="full-name-error" className="text-xs text-destructive">
                  {fieldErrors.fullName}
                </p>
              )}
            </div>

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
                autoComplete="new-password"
              />
              {fieldErrors.password && (
                <p id="password-error" className="text-xs text-destructive">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {registerMutation.isError && (
              <div
                role="alert"
                className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {authErrorMessage(registerMutation.error)}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={pending}>
              {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {pending ? "正在注册…" : "注册"}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              已有账号？
              <Link
                to="/login"
                search={{ redirect: redirectTarget }}
                className="text-primary hover:underline"
              >
                登录
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
