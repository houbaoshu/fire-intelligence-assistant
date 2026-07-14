import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { BackendStatusCard } from "@/components/common/BackendStatus";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { PageHeader } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { API_BASE_URL } from "@/lib/api-client";
import { systemService } from "@/lib/services/system";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "设置 · 消防智能助手" }] }),
  component: SettingsPage,
});

const PREF_KEY = "fip.prefs.v1";
type Prefs = { compactUi: boolean; reducedMotion: boolean };
const DEFAULT_PREFS: Prefs = { compactUi: false, reducedMotion: false };

function loadPrefs(): Prefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const value = JSON.parse(window.localStorage.getItem(PREF_KEY) || "{}") as Record<
      string,
      unknown
    >;
    return {
      compactUi: typeof value.compactUi === "boolean" ? value.compactUi : false,
      reducedMotion: typeof value.reducedMotion === "boolean" ? value.reducedMotion : false,
    };
  } catch {
    return DEFAULT_PREFS;
  }
}

function SettingsPage() {
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const [ready, setReady] = useState(false);
  const capabilities = useQuery({
    queryKey: ["system-capabilities"],
    queryFn: ({ signal }) => systemService.capabilities(signal),
  });
  const apiOrigin = useMemo(() => {
    try {
      return new URL(API_BASE_URL).origin;
    } catch {
      return "未配置";
    }
  }, []);

  useEffect(() => {
    setPrefs(loadPrefs());
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    document.documentElement.classList.toggle("compact-ui", prefs.compactUi);
    document.documentElement.classList.toggle("reduce-motion", prefs.reducedMotion);
    try {
      window.localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
    } catch {
      // Preferences remain active for this session if persistence is unavailable.
    }
  }, [prefs, ready]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="设置"
        description="这里只保存非敏感界面偏好；密钥和部署参数不能在浏览器中修改。"
      />
      <BackendStatusCard />
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">连接</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <span className="text-muted-foreground">API 来源：</span>
          <span className="font-mono">{apiOrigin}</span>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">界面与辅助功能</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <PreferenceRow
            id="compact"
            label="紧凑界面"
            description="减少主要区域和卡片间距。"
            checked={prefs.compactUi}
            onChange={(value) => setPrefs((current) => ({ ...current, compactUi: value }))}
          />
          <PreferenceRow
            id="motion"
            label="减少动态效果"
            description="关闭非必要过渡和旋转效果。"
            checked={prefs.reducedMotion}
            onChange={(value) => setPrefs((current) => ({ ...current, reducedMotion: value }))}
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              if (window.confirm("恢复所有界面偏好为默认值？登录状态和业务数据不会受影响。")) {
                setPrefs(DEFAULT_PREFS);
              }
            }}
          >
            恢复默认
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">系统能力</CardTitle>
        </CardHeader>
        <CardContent>
          {capabilities.isLoading ? (
            <LoadingState />
          ) : capabilities.error ? (
            <ErrorState
              description={capabilities.error.message}
              onRetry={() => capabilities.refetch()}
            />
          ) : (
            capabilities.data && (
              <div className="space-y-2 text-sm">
                <div>版本：{capabilities.data.application_version}</div>
                <div>环境：{capabilities.data.environment}</div>
                <ul className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                  {Object.entries(capabilities.data.features).map(([name, available]) => (
                    <li key={name}>
                      {name}：{available ? "可用" : "未配置"}
                    </li>
                  ))}
                </ul>
              </div>
            )
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function PreferenceRow({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <Label htmlFor={id}>{label}</Label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  );
}
