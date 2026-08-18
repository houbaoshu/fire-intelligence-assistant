import { api } from "../api-client";
import type { Paginated } from "./common";

/**
 * AI 平台管理服务(Milestone 8):严格对齐 docs/API.md §12(AI 平台管理)。
 * 全部端点位于 /api/admin 前缀下,仅 admin 角色可访问;后端校验为权威,
 * 前端只负责展示后端返回的可读错误。
 */

/** Prompt 版本对象。GET /api/admin/prompts 返回全部版本(含历史版本)。 */
export type PromptVersion = {
  id: string;
  key: string;
  name: string | null;
  description: string | null;
  content: string;
  version: number;
  is_active: boolean;
  created_at: string;
};

/** 创建 Prompt 新版本请求体(版本号由后端递增)。 */
export type PromptVersionCreateBody = {
  content: string;
  name?: string;
  description?: string;
};

/** 模型能力类型(定义权:docs/DATABASE.md model_configurations)。 */
export type ModelKind = "llm" | "vision" | "ocr" | "speech" | "embedding" | "reranker";

export const MODEL_KINDS: ModelKind[] = ["llm", "vision", "ocr", "speech", "embedding", "reranker"];

/** 模型配置对象。api_key_ref 只是密钥环境变量名,后端不返回密钥本身。 */
export type ModelConfiguration = {
  id: string;
  name: string;
  kind: ModelKind;
  provider: string;
  model_name: string;
  base_url: string | null;
  api_key_ref: string | null;
  is_active: boolean;
  priority: number;
};

/** 新建模型配置请求体。 */
export type ModelCreateBody = {
  name: string;
  kind: ModelKind;
  provider: string;
  model_name: string;
  base_url?: string;
  api_key_ref?: string;
  is_active?: boolean;
  priority?: number;
};

/** 更新模型配置请求体(字段可选,仅提交变更项)。 */
export type ModelUpdateBody = Partial<ModelCreateBody>;

/** 删除模型配置响应信封。 */
export type ModelDeleteResponse = {
  id: string;
  deleted: boolean;
};

/** 评估问题定义。expected_keywords 为空数组时不提交该字段。 */
export type EvaluationQuestion = {
  question: string;
  expected_keywords?: string[];
  require_source?: boolean;
};

/** 运行评估请求体(同步执行,真实调用 RAG+LLM 管线,可能耗时较长)。 */
export type EvaluationRunBody = {
  name: string;
  questions: EvaluationQuestion[];
};

/** 评估运行列表项。 */
export type EvaluationRun = {
  id: string;
  name: string;
  status: string;
  total_questions: number;
  passed: number;
  created_at: string;
};

/**
 * 评估运行详情:在列表项基础上附加逐题明细。
 * details 内部结构由后端定义,前端容错渲染(结构未知时原样展示 JSON)。
 */
export type EvaluationRunDetail = EvaluationRun & {
  details: unknown;
};

export type EvaluationListParams = {
  page?: number;
  page_size?: number;
};

/** 服务端插件注册项(定义权:docs/DATABASE.md plugins)。 */
export type AdminPlugin = {
  id: string;
  name: string;
  version: string | null;
  description: string | null;
  entry_point: string;
  enabled: boolean;
};

const base = "/api/admin";

export const aiPlatformService = {
  // ---- Prompt 管理 ----
  /** 返回全部 Prompt 的全部版本;前端按 key 分组展示。 */
  listPrompts: (signal?: AbortSignal) =>
    api.get<{ items: PromptVersion[] }>(`${base}/prompts`, { signal }),
  /** 基于给定内容创建某 key 的新版本(不自动生效)。 */
  createPromptVersion: (key: string, body: PromptVersionCreateBody) =>
    api.post<PromptVersion>(`${base}/prompts/${encodeURIComponent(key)}/versions`, body),
  /** 激活指定版本;后端保证同 key 仅一个生效版本。 */
  activatePrompt: (id: string) =>
    api.post<Pick<PromptVersion, "id" | "is_active">>(
      `${base}/prompts/${encodeURIComponent(id)}/activate`,
    ),

  // ---- 模型配置 ----
  listModels: (signal?: AbortSignal) =>
    api.get<{ items: ModelConfiguration[] }>(`${base}/models`, { signal }),
  createModel: (body: ModelCreateBody) => api.post<ModelConfiguration>(`${base}/models`, body),
  updateModel: (id: string, body: ModelUpdateBody) =>
    api.put<ModelConfiguration>(`${base}/models/${encodeURIComponent(id)}`, body),
  deleteModel: (id: string) =>
    api.delete<ModelDeleteResponse>(`${base}/models/${encodeURIComponent(id)}`),

  // ---- 评估运行 ----
  /** 同步执行评估:真实调用检索与模型管线,响应可能较慢。 */
  runEvaluation: (body: EvaluationRunBody) =>
    api.post<EvaluationRunDetail>(`${base}/evaluations`, body),
  listEvaluations: (params: EvaluationListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<EvaluationRun>>(`${base}/evaluations`, {
      query: { page: params.page, page_size: params.page_size },
      signal,
    }),
  getEvaluation: (id: string, signal?: AbortSignal) =>
    api.get<EvaluationRunDetail>(`${base}/evaluations/${encodeURIComponent(id)}`, { signal }),

  // ---- 插件管理 ----
  listPlugins: (signal?: AbortSignal) =>
    api.get<{ items: AdminPlugin[] }>(`${base}/plugins`, { signal }),
  /** 仅支持切换启用状态;失败时前端回滚开关并展示后端可读错误。 */
  updatePlugin: (id: string, enabled: boolean) =>
    api.put<AdminPlugin>(`${base}/plugins/${encodeURIComponent(id)}`, { enabled }),
};
