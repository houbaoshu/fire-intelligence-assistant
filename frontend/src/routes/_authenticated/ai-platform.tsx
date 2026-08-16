import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Brain, RefreshCw, Save } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/StateViews";
import { api } from "@/lib/api-client";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/ai-platform")({
  head: () => ({
    meta: [
      { title: "AI 平台 · 消防智能助手" },
      { name: "description", content: "Prompt、模型、评估与插件管理。" },
    ],
  }),
  component: AIPlatformPage,
});

type PromptItem = {
  id: string;
  key: string;
  name: string;
  description: string | null;
  version: number;
  is_active: boolean;
  updated_at: string;
};

type PromptDetail = PromptItem & { content: string };

type ModelItem = {
  id: string;
  name: string;
  kind: string;
  provider: string;
  model_name: string;
  base_url: string | null;
  api_key_ref: string | null;
  is_active: boolean;
  priority: number;
};

type PluginItem = {
  id: string;
  name: string;
  version: string;
  description: string | null;
  enabled: boolean;
};
type EvalItem = {
  id: string;
  name: string;
  status: string;
  total_questions: number;
  passed: number;
  created_at: string;
};

const KIND_LABELS: Record<string, string> = {
  llm: "LLM",
  vision: "视觉",
  ocr: "OCR",
  speech: "语音",
  embedding: "Embedding",
  reranker: "Reranker",
};

function AIPlatformPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"prompts" | "models" | "plugins" | "evals">("prompts");

  if (user?.role !== "admin") {
    return (
      <div className="mx-auto max-w-3xl">
        <PageHeader
          title="AI 平台"
          description="仅管理员可管理 AI 平台配置。"
          actions={
            <Button variant="outline" onClick={() => navigate({ to: "/" })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> 返回工作台
            </Button>
          }
        />
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            您没有管理 AI 平台配置的权限。
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="AI 平台"
        description="管理 Prompt 目录、模型配置、插件与评估运行。所有配置只作用于后端,不暴露密钥。"
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Tab active={tab === "prompts"} onClick={() => setTab("prompts")} label="Prompt 目录" />
        <Tab active={tab === "models"} onClick={() => setTab("models")} label="模型配置" />
        <Tab active={tab === "plugins"} onClick={() => setTab("plugins")} label="插件" />
        <Tab active={tab === "evals"} onClick={() => setTab("evals")} label="评估" />
      </div>
      {tab === "prompts" && <PromptsTab />}
      {tab === "models" && <ModelsTab />}
      {tab === "plugins" && <PluginsTab />}
      {tab === "evals" && <EvalsTab />}
    </div>
  );
}

function Tab({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition " +
        (active
          ? "bg-primary text-primary-foreground"
          : "bg-card text-muted-foreground hover:bg-accent")
      }
    >
      <Brain className="h-4 w-4" />
      {label}
    </button>
  );
}

function PromptsTab() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<PromptDetail | null>(null);
  const [content, setContent] = useState("");

  const query = useQuery({
    queryKey: ["ai-prompts"],
    queryFn: ({ signal }) =>
      api.get<{ items: PromptItem[]; total: number }>("/api/ai-platform/prompts", { signal }),
  });

  const updateMutation = useMutation({
    mutationFn: (p: PromptDetail) =>
      api.put("/api/ai-platform/prompts/" + encodeURIComponent(p.id), { content }),
    onSuccess: () => {
      toast.success("Prompt 已更新(新版本已生效)");
      setSelected(null);
      qc.invalidateQueries({ queryKey: ["ai-prompts"] });
    },
    onError: (e) => toast.error("更新失败:" + e.message),
  });

  const open = async (id: string) => {
    try {
      const p = await api.get<PromptDetail>("/api/ai-platform/prompts/" + encodeURIComponent(id));
      setSelected(p);
      setContent(p.content);
    } catch (e) {
      toast.error("加载失败:" + (e as Error).message);
    }
  };

  if (selected) {
    return (
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">
            {selected.key} (v{selected.version})
          </CardTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setSelected(null)}>
              返回
            </Button>
            <Button
              size="sm"
              onClick={() => updateMutation.mutate(selected)}
              disabled={!content.trim() || updateMutation.isPending}
            >
              <Save className="mr-2 h-3.5 w-3.5" /> 保存为新版本
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Textarea
            rows={16}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="font-mono text-xs"
          />
          <p className="mt-2 text-xs text-muted-foreground">
            保存会创建新版本并激活,旧版本保留可追溯。
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">Prompt 目录</CardTitle>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")} />{" "}
          刷新
        </Button>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
        ) : (
          <div className="divide-y">
            {query.data?.items.map((p) => (
              <button
                key={p.id}
                onClick={() => open(p.id)}
                className="flex w-full items-center justify-between py-2.5 text-left hover:bg-accent/40"
              >
                <div>
                  <div className="text-sm font-medium">{p.key}</div>
                  <div className="text-xs text-muted-foreground">
                    v{p.version}
                    {p.is_active ? " · 生效中" : " · 已停用"}
                    {p.description ? " · " + p.description : ""}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">编辑 →</span>
              </button>
            ))}
            {query.data && query.data.items.length === 0 && <EmptyState title="暂无 Prompt" />}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ModelsTab() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["ai-models"],
    queryFn: ({ signal }) => api.get<{ items: ModelItem[] }>("/api/ai-platform/models", { signal }),
  });
  const activate = useMutation({
    mutationFn: (id: string) =>
      api.post("/api/ai-platform/models/" + encodeURIComponent(id) + "/activate"),
    onSuccess: () => {
      toast.success("已激活");
      qc.invalidateQueries({ queryKey: ["ai-models"] });
    },
    onError: (e) => toast.error("操作失败:" + e.message),
  });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">模型配置(按能力路由)</CardTitle>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")} />{" "}
          刷新
        </Button>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
        ) : (
          <div className="divide-y">
            {query.data?.items.map((m) => (
              <div key={m.id} className="flex items-center justify-between gap-3 py-2.5">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {m.name}
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {KIND_LABELS[m.kind] ?? m.kind}
                    </span>
                    {m.is_active && <span className="text-xs text-emerald-600">生效中</span>}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {m.provider} · {m.model_name}
                    {m.api_key_ref ? " · 密钥:" + m.api_key_ref : ""}
                  </div>
                </div>
                {!m.is_active && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => activate.mutate(m.id)}
                    disabled={activate.isPending}
                  >
                    激活
                  </Button>
                )}
              </div>
            ))}
            {query.data && query.data.items.length === 0 && (
              <EmptyState
                title="暂无模型配置"
                description="模型默认来自环境变量;添加配置后按能力路由。"
              />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PluginsTab() {
  const query = useQuery({
    queryKey: ["ai-plugins"],
    queryFn: ({ signal }) =>
      api.get<{ items: PluginItem[] }>("/api/ai-platform/plugins", { signal }),
  });
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">插件(服务端执行)</CardTitle>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")} />{" "}
          刷新
        </Button>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
        ) : (
          <div className="divide-y">
            {query.data?.items.map((p) => (
              <div key={p.id} className="py-2.5">
                <div className="flex items-center gap-2 text-sm font-medium">
                  {p.name} <span className="text-xs text-muted-foreground">v{p.version}</span>
                </div>
                <div className="text-xs text-muted-foreground">{p.description}</div>
              </div>
            ))}
            {query.data && query.data.items.length === 0 && <EmptyState title="暂无插件" />}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EvalsTab() {
  const qc = useQueryClient();
  const [questions, setQuestions] = useState("");
  const query = useQuery({
    queryKey: ["ai-evals"],
    queryFn: ({ signal }) =>
      api.get<{ items: EvalItem[] }>("/api/ai-platform/evaluations", { signal }),
  });
  const run = useMutation({
    mutationFn: () =>
      api.post<{ passed: number; total_questions: number }>("/api/ai-platform/evaluations/run", {
        name: "手动评估 " + new Date().toLocaleString("zh-CN"),
        questions: questions
          .split("\n")
          .map((q) => q.trim())
          .filter(Boolean),
      }),
    onSuccess: (res) => {
      toast.success("评估完成:" + res.passed + "/" + res.total_questions + " 通过");
      qc.invalidateQueries({ queryKey: ["ai-evals"] });
    },
    onError: (e) => toast.error("评估失败:" + e.message),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">运行评估(真实 RAG+LLM 管线)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            rows={6}
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
            placeholder={"每行一个问题,例如:\n安全出口被锁闭适用哪些规定?"}
          />
          <Button onClick={() => run.mutate()} disabled={!questions.trim() || run.isPending}>
            {run.isPending ? "评估中…" : "运行评估"}
          </Button>
          <p className="text-xs text-muted-foreground">
            评估真实调用检索与生成管线,按「有回答 / 有来源 / 回答长度合理」计分,不编造结果。
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">历史评估</CardTitle>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw className={"mr-2 h-3.5 w-3.5 " + (query.isFetching ? "animate-spin" : "")} />{" "}
            刷新
          </Button>
        </CardHeader>
        <CardContent>
          {query.isLoading ? (
            <LoadingState />
          ) : query.isError ? (
            <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
          ) : (
            <div className="divide-y">
              {query.data?.items.map((e) => (
                <div key={e.id} className="py-2.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{e.name}</span>
                    <span
                      className={
                        "text-xs " +
                        (e.passed === e.total_questions ? "text-emerald-600" : "text-amber-600")
                      }
                    >
                      {e.passed}/{e.total_questions} 通过
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(e.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
              ))}
              {query.data && query.data.items.length === 0 && <EmptyState title="暂无评估记录" />}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
