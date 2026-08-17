import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { API_BASE_URL } from "@/lib/api-client";
import {
  DEFAULT_PREFERENCES,
  PAGE_SIZE_OPTIONS,
  applyPreferences,
  loadPreferences,
  savePreferences,
  type DensityPref,
  type Preferences,
  type ThemePref,
} from "@/lib/preferences";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "设置 · 消防智能助手" },
      { name: "description", content: "查看后端连接信息并管理本地界面偏好。" },
    ],
  }),
  component: SettingsPage,
});

/** 展示用的安全 API origin:去除 query、hash 与凭据(specs/settings.md)。 */
function safeApiOrigin(): string {
  if (!API_BASE_URL) return "不可用(未配置 VITE_API_BASE_URL)";
  try {
    const url = new URL(API_BASE_URL);
    return url.origin + (url.pathname === "/" ? "" : url.pathname);
  } catch {
    return "不可用(配置无法解析)";
  }
}

function SettingsPage() {
  const [prefs, setPrefs] = useState<Preferences>(DEFAULT_PREFERENCES);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setPrefs(loadPreferences());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    savePreferences(prefs);
    applyPreferences(prefs);
  }, [prefs, ready]);

  const patch = (p: Partial<Preferences>) => setPrefs((prev) => ({ ...prev, ...p }));

  const resetDefaults = () => {
    if (
      window.confirm(
        "恢复默认值将变更:主题(跟随系统)、显示密度(舒适)、减弱动效(关闭)、列表默认每页条数(20)。认证信息与业务数据不受影响。确认继续?",
      )
    ) {
      setPrefs(DEFAULT_PREFERENCES);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="设置"
        description="查看后端连接信息并管理本地界面偏好。敏感配置(如密钥)通过部署环境变量管理,不在浏览器中修改。"
      />

      <section aria-label="连接">
        <BackendStatusCard />
        <p className="mt-2 text-xs text-muted-foreground">
          API 来源:<span className="font-mono text-foreground">{safeApiOrigin()}</span>
          (已去除 query 与凭据;普通用户不可修改 API Base URL)
        </p>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">外观与无障碍</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="pref-theme">主题</Label>
              <p className="text-xs text-muted-foreground">浅色 / 深色 / 跟随系统。</p>
            </div>
            <Select value={prefs.theme} onValueChange={(v) => patch({ theme: v as ThemePref })}>
              <SelectTrigger id="pref-theme" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">浅色</SelectItem>
                <SelectItem value="dark">深色</SelectItem>
                <SelectItem value="system">跟随系统</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="pref-density">显示密度</Label>
              <p className="text-xs text-muted-foreground">紧凑模式减少页面间距。</p>
            </div>
            <Select
              value={prefs.density}
              onValueChange={(v) => patch({ density: v as DensityPref })}
            >
              <SelectTrigger id="pref-density" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="comfortable">舒适</SelectItem>
                <SelectItem value="compact">紧凑</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="pref-motion">减弱动效</Label>
              <p className="text-xs text-muted-foreground">减少界面过渡与动画。</p>
            </div>
            <Switch
              id="pref-motion"
              checked={prefs.reducedMotion}
              onCheckedChange={(v) => patch({ reducedMotion: v })}
            />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="pref-page-size">列表默认每页条数</Label>
              <p className="text-xs text-muted-foreground">应用于各业务记录列表页。</p>
            </div>
            <Select
              value={String(prefs.pageSize)}
              onValueChange={(v) => patch({ pageSize: Number(v) })}
            >
              <SelectTrigger id="pref-page-size" className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n} 条 / 页
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="pt-2">
            <Button variant="outline" size="sm" onClick={resetDefaults}>
              恢复默认值
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">应用信息</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          <div>
            前端版本:<span className="font-mono text-foreground">0.1.0 · Frontend Foundation</span>
          </div>
          <div className="mt-1">
            偏好仅保存在本浏览器(localStorage),不同步到服务端;本页面不展示、不存储任何 API
            key、token 或数据库配置。用户与角色管理、模型管理等能力不在 v1 范围内。
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
