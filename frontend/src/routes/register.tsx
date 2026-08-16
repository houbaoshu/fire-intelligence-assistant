import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Loader2, Lock, Mail, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api-client";

export const Route = createFileRoute("/register")({
  head: () => ({
    meta: [
      { title: "注册 · 消防智能助手" },
      { name: "description", content: "注册消防智能助手账号。" },
    ],
  }),
  component: RegisterPage,
});

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function RegisterPage() {
  const { register, status } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "authenticated") {
    void navigate({ to: "/", replace: true });
  }

  const emailValid = EMAIL_RE.test(email.trim());
  const passwordValid = password.length >= 8;
  const confirmValid = password === confirm;
  const canSubmit = emailValid && passwordValid && confirmValid && !submitting;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await register(email.trim(), password, fullName.trim() || undefined);
      await navigate({ to: "/", replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("注册功能暂未开放,请联系管理员开通账号。");
      } else {
        setError(err instanceof ApiError ? err.message : "注册失败,请稍后重试");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">注册</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">创建账号</CardTitle>
          <CardDescription>注册后即可使用各业务模块</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="fullName">姓名(可选)</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-9"
                  placeholder="张三"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                  placeholder="user@example.com"
                />
              </div>
              {email.trim() && !emailValid && (
                <p className="text-xs text-destructive">请输入合法的邮箱地址</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  placeholder="至少 8 位"
                />
              </div>
              {password && !passwordValid && (
                <p className="text-xs text-destructive">密码至少需要 8 位</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">确认密码</Label>
              <Input
                id="confirm"
                type="password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="再次输入密码"
              />
              {confirm && !confirmValid && (
                <p className="text-xs text-destructive">两次输入的密码不一致</p>
              )}
            </div>

            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={!canSubmit}>
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              注册
            </Button>
          </form>

          <div className="mt-4 text-center text-sm text-muted-foreground">
            已有账号?
            <Link to="/login" className="ml-1 font-medium text-primary hover:underline">
              去登录
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
