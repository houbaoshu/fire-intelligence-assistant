import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "设置 · 消防智能助手" },
      { name: "description", content: "查看后端连接信息并管理本地界面偏好。" },
    ],
  }),
  component: SettingsPage,
});

const PREF_KEY = "fip.prefs.v1";

type Prefs = { compactUi: boolean };
const DEFAULT_PREFS: Prefs = { compactUi: false };

function loadPrefs(): Prefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = window.localStorage.getItem(PREF_KEY);
    if (!raw) return DEFAULT_PREFS;
    return { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<Prefs>) };
  } catch {
    return DEFAULT_PREFS;
  }
}

function SettingsPage() {
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setPrefs(loadPrefs());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
    } catch {
      /* ignore */
    }
  }, [prefs, ready]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="设置"
        description="查看后端连接信息并管理本地界面偏好。敏感配置(如密钥)通过部署环境变量管理,不在浏览器中修改。"
      />

      <BackendStatusCard />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">界面偏好</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="compact">紧凑界面</Label>
              <p className="text-xs text-muted-foreground">减少间距以在较小屏幕上显示更多内容。</p>
            </div>
            <Switch
              id="compact"
              checked={prefs.compactUi}
              onCheckedChange={(v) => setPrefs((p) => ({ ...p, compactUi: v }))}
            />
          </div>
          <div className="pt-2">
            <Button variant="outline" size="sm" onClick={() => setPrefs(DEFAULT_PREFS)}>
              恢复默认
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">系统信息</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          <div>
            版本:<span className="font-mono text-foreground">0.1.0 · Frontend Foundation</span>
          </div>
          <div className="mt-1">
            用户角色、模型管理、密钥配置等能力需管理员及后端契约支持,当前版本不提供。
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
