import { CheckCircle2, Loader2, PlugZap, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { API_BASE_URL } from "@/lib/api-client";

export function BackendStatusBadge({ compact = false }: { compact?: boolean }) {
  const { health, refetch, isFetching } = useBackendHealth();

  const label =
    health.state === "unconfigured"
      ? "未配置 API"
      : health.state === "connected"
        ? "后端已连接"
        : health.state === "disconnected"
          ? "后端不可达"
          : "检查中";

  const icon =
    health.state === "connected" ? (
      <CheckCircle2 className="h-3.5 w-3.5" />
    ) : health.state === "disconnected" || health.state === "unconfigured" ? (
      <XCircle className="h-3.5 w-3.5" />
    ) : (
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
    );

  const tone =
    health.state === "connected"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
      : health.state === "disconnected" || health.state === "unconfigured"
        ? "border-destructive/40 bg-destructive/10 text-destructive"
        : "border-border bg-muted text-muted-foreground";

  return (
    <div className={cn("inline-flex items-center gap-2", compact && "text-xs")}>
      <Badge variant="outline" className={cn("gap-1.5", tone)}>
        {icon}
        {label}
      </Badge>
      {!compact && (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => refetch()}
          disabled={isFetching || health.state === "unconfigured"}
        >
          <RefreshCw className={cn("mr-1 h-3.5 w-3.5", isFetching && "animate-spin")} />
          重新检查
        </Button>
      )}
    </div>
  );
}

export function BackendStatusCard() {
  const { health, refetch, isFetching } = useBackendHealth();
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <PlugZap className="h-4 w-4 text-muted-foreground" /> 后端连接
        </div>
        <BackendStatusBadge compact />
      </div>
      <div className="mt-2 text-xs text-muted-foreground">
        目标地址:
        <span className="ml-1 font-mono text-foreground">
          {API_BASE_URL || "(未设置 VITE_API_BASE_URL)"}
        </span>
      </div>
      {health.state === "disconnected" && (
        <div className="mt-2 text-xs text-destructive">错误:{health.error}</div>
      )}
      <div className="mt-3">
        <Button
          size="sm"
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching || health.state === "unconfigured"}
        >
          <RefreshCw className={cn("mr-2 h-3.5 w-3.5", isFetching && "animate-spin")} />
          重新检查
        </Button>
      </div>
    </div>
  );
}
