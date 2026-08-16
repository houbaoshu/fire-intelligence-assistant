import { AlertTriangle, Inbox, Loader2, CheckCircle2, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type BaseProps = {
  title?: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
};

function Frame({
  icon,
  title,
  description,
  action,
  className,
  tone,
}: BaseProps & { icon: ReactNode; tone?: "default" | "danger" | "success" }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/50 px-6 py-10 text-center",
        tone === "danger" && "border-destructive/40 bg-destructive/5",
        tone === "success" && "border-emerald-500/40 bg-emerald-500/5",
        className,
      )}
    >
      <div
        className={cn(
          "mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground",
          tone === "danger" && "bg-destructive/10 text-destructive",
          tone === "success" && "bg-emerald-500/10 text-emerald-600",
        )}
      >
        {icon}
      </div>
      {title && <div className="text-sm font-medium text-foreground">{title}</div>}
      {description && (
        <div className="mt-1 max-w-md text-sm text-muted-foreground">{description}</div>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function LoadingState({ title = "加载中…", description, className }: BaseProps) {
  return (
    <Frame
      icon={<Loader2 className="h-5 w-5 animate-spin" />}
      title={title}
      description={description}
      className={className}
    />
  );
}

export function EmptyState({ title = "暂无数据", description, action, className }: BaseProps) {
  return (
    <Frame
      icon={<Inbox className="h-5 w-5" />}
      title={title}
      description={description}
      action={action}
      className={className}
    />
  );
}

export function ErrorState({
  title = "加载失败",
  description,
  action,
  onRetry,
  className,
}: BaseProps & { onRetry?: () => void }) {
  return (
    <Frame
      tone="danger"
      icon={<AlertTriangle className="h-5 w-5" />}
      title={title}
      description={description}
      action={
        action ??
        (onRetry ? (
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" /> 重试
          </Button>
        ) : undefined)
      }
      className={className}
    />
  );
}

export function SuccessState({ title = "已完成", description, action, className }: BaseProps) {
  return (
    <Frame
      tone="success"
      icon={<CheckCircle2 className="h-5 w-5" />}
      title={title}
      description={description}
      action={action}
      className={className}
    />
  );
}

export function UnavailableState({
  title = "该功能暂未可用",
  description = "对应的后端接口尚未就绪。此页面将在服务上线后自动生效。",
  className,
}: BaseProps) {
  return (
    <Frame
      icon={<AlertTriangle className="h-5 w-5" />}
      title={title}
      description={description}
      className={className}
    />
  );
}
