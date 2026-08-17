import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Bell, Check, CheckCheck, XCircle, CheckCircle2, Info } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { notificationService, type AppNotification } from "@/lib/services/notifications";
import { formatRelativeTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

/** 未读数轮询间隔;任务终态回调等场景由调用方 invalidate 立即刷新。 */
const POLL_INTERVAL_MS = 30_000;
const PAGE_SIZE = 10;

/** 通知类型 → 图标;未知类型使用通用图标(不依赖后端文案)。 */
function TypeIcon({ type }: { type: string }) {
  const cls = "mt-0.5 h-4 w-4 shrink-0";
  if (type.includes("fail")) return <XCircle className={cn(cls, "text-destructive")} />;
  if (type.includes("complete") || type.includes("success"))
    return <CheckCircle2 className={cn(cls, "text-emerald-600")} />;
  return <Info className={cn(cls, "text-muted-foreground")} />;
}

/**
 * 通知 → 业务页面的安全导航映射(按 entity_type;映射不到返回 null 不跳转)。
 * entity_type 取值由后端定义,此处仅白名单映射,未知值安全忽略。
 */
function useNotificationNavigate() {
  const navigate = useNavigate();
  return (n: AppNotification): boolean => {
    const id = n.entity_id;
    switch (n.entity_type) {
      case "inspection_record":
        if (!id) return false;
        void navigate({ to: "/inspection-record/$id", params: { id } });
        return true;
      case "photo_report":
        if (!id) return false;
        void navigate({ to: "/photo-report/$id", params: { id } });
        return true;
      case "interview_record":
        if (!id) return false;
        void navigate({ to: "/interview-record/$id", params: { id } });
        return true;
      case "knowledge_document":
      case "knowledge_index_job":
        void navigate({ to: "/knowledge-base" });
        return true;
      case "ai_task":
        void navigate({ to: "/tasks" });
        return true;
      default:
        return false;
    }
  };
}

function NotificationItem({
  notification,
  onNavigate,
}: {
  notification: AppNotification;
  onNavigate: () => void;
}) {
  const queryClient = useQueryClient();
  const navigateTo = useNotificationNavigate();
  const unread = notification.read_at === null;

  const markReadMutation = useMutation({
    mutationFn: () => notificationService.markRead(notification.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "标记已读失败");
    },
  });

  const handleOpen = () => {
    if (unread) markReadMutation.mutate();
    if (navigateTo(notification)) onNavigate();
  };

  return (
    <div className={cn("flex gap-2 rounded-md px-2 py-2 text-left", unread && "bg-primary/5")}>
      <TypeIcon type={notification.type} />
      <div className="min-w-0 flex-1">
        <button
          type="button"
          onClick={handleOpen}
          className="block w-full rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "truncate text-sm",
                unread ? "font-medium text-foreground" : "text-muted-foreground",
              )}
            >
              {notification.title}
            </span>
            {unread && (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-label="未读" />
            )}
          </div>
          {notification.body && (
            <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
              {notification.body}
            </div>
          )}
          <div className="mt-1 text-[10px] text-muted-foreground">
            {formatRelativeTime(notification.created_at)}
          </div>
        </button>
      </div>
      {unread && (
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0"
          aria-label="标记为已读"
          title="标记为已读"
          disabled={markReadMutation.isPending}
          onClick={() => markReadMutation.mutate()}
        >
          <Check className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}

/** 应用头部通知铃铛:未读数徽章 + 最近通知 Popover。 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: ({ signal }) => notificationService.list({ page_size: PAGE_SIZE }, signal),
    refetchInterval: POLL_INTERVAL_MS,
    retry: 1,
  });

  const markAllMutation = useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "全部标记已读失败");
    },
  });

  const unreadCount = listQuery.data?.unread_count ?? 0;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-8 w-8"
          aria-label={unreadCount > 0 ? `通知,${unreadCount} 条未读` : "通知"}
          title="通知"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span
              aria-hidden
              className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[9px] font-medium text-destructive-foreground"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0">
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <span className="text-sm font-medium">通知</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            disabled={markAllMutation.isPending || unreadCount === 0}
            onClick={() => markAllMutation.mutate()}
          >
            <CheckCheck className="mr-1 h-3.5 w-3.5" /> 全部已读
          </Button>
        </div>
        <div className="max-h-96 overflow-y-auto p-1">
          {listQuery.isLoading ? (
            <LoadingState title="加载通知…" className="border-0 py-8" />
          ) : listQuery.error ? (
            <ErrorState
              title="通知不可用"
              description={listQuery.error instanceof Error ? listQuery.error.message : "加载失败"}
              onRetry={() => listQuery.refetch()}
              className="border-0 py-8"
            />
          ) : !listQuery.data || listQuery.data.items.length === 0 ? (
            <EmptyState title="暂无通知" className="border-0 py-8" />
          ) : (
            listQuery.data.items.map((n) => (
              <NotificationItem key={n.id} notification={n} onNavigate={() => setOpen(false)} />
            ))
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
