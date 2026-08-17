import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Link,
  createRootRouteWithContext,
  redirect,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { ApiError, hasAuthSession } from "../lib/api-client";
import { applyPreferences, loadPreferences } from "../lib/preferences";
import { authMeQueryOptions } from "../lib/services/auth";
import { AuthProvider } from "../components/auth/AuthProvider";
import { AppShell } from "../components/layout/AppShell";
import { Toaster } from "../components/ui/sonner";

/** 公开页面：无需会话即可访问。 */
const PUBLIC_PATHS = new Set(["/login", "/register"]);

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  // 集中式路由守卫：所有非公开页面都要求有效会话。
  // 授权本身仍由后端逐次校验，此处只做会话门禁。
  beforeLoad: async ({ location, context }) => {
    // localStorage 仅客户端可访问；SSR 阶段跳过，由客户端水合时的 beforeLoad 与
    // AppShell 的初始化门禁兜底，避免闪现受保护内容。
    if (typeof window === "undefined") return;
    if (PUBLIC_PATHS.has(location.pathname)) return;
    if (!hasAuthSession()) {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
    try {
      // 进入受保护路由时用 GET /api/auth/me 校验身份；access_token 过期由 api-client 透明续期。
      await context.queryClient.ensureQueryData(authMeQueryOptions());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // refresh 已失败且会话被清除；携带原目标跳转登录页，登录成功后恢复。
        throw redirect({ to: "/login", search: { redirect: location.href } });
      }
      // 网络错误 / 后端不可用：不清除会话、不跳转，交由页面级错误态展示。
    }
  },
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "消防智能助手 · Fire Intelligence Platform" },
      {
        name: "description",
        content:
          "面向消防监督执法的智能辅助平台:法规问答、检查记录、图像报告、询问笔录与知识库管理。",
      },
      { name: "author", content: "Fire Intelligence Platform" },
      { property: "og:title", content: "消防智能助手 · Fire Intelligence Platform" },
      {
        property: "og:description",
        content:
          "面向消防监督执法的智能辅助平台:法规问答、检查记录、图像报告、询问笔录与知识库管理。",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  // 启动时应用本地偏好(主题 / 密度 / 减弱动效);system 主题跟随系统变化。
  useEffect(() => {
    applyPreferences(loadPreferences());
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const prefs = loadPreferences();
      if (prefs.theme === "system") applyPreferences(prefs);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
      <Toaster />
    </QueryClientProvider>
  );
}
