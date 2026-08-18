# ARCHITECTURE.md

# Fire Intelligence Platform 系统架构

> 现状说明：`frontend/` 与 `backend/` 均未实现，仓库当前只有权威文档。前端代码必须由模型依据本文档与 `specs/` 从零设计并生成，禁止复制任何外部脚手架产物；后端按本文 §7 的目标结构以 Node.js + TypeScript 实现。

本文档是"架构"类别的唯一权威文件，定义系统边界、前后端职责、模块组织、数据流、AI 编排、异步任务与存储职责。编码规则见 `AGENTS.md`，接口契约见 `API.md`，表结构与枚举见 `DATABASE.md`。

---

## 1. 系统概览

Fire Intelligence Platform 是一个面向消防安全检查工作的 AI 辅助系统。

平台能力：

- 消防法规问答（regulation QA）
- 检查记录生成（inspection record）
- 拍照报告生成（photo report）
- 询问记录生成（interview record）
- 知识库管理
- 文档生成（Word / PDF）
- 文件上传与存储
- 任务进度跟踪
- 用户与权限管理
- 统计与审计记录

系统采用前后端分离架构：

```text
User
  |
  v
Frontend（Web SPA，技术栈由实现时按 §4.1 原则选定）
  |
  | HTTPS / REST API
  v
Node.js Backend (TypeScript)
  |
  +-------------------+
  |                   |
  v                   v
Business Services    AI Orchestrator
  |                   |
  v                   +---------------------------+
PostgreSQL            |       |       |           |
                      v       v       v           v
                     LLM    Vision   OCR      Speech Recognition
                      |
                      v
                     RAG
                      |
                      v
                 Vector Database
```

---

## 2. 架构原则

1. 前端只负责展示与用户交互。
2. 后端拥有全部业务逻辑。
3. AI 推理只在后端运行。
4. PostgreSQL 是业务数据的唯一权威来源。
5. 对象存储保存上传与生成的文件。
6. 向量数据库只保存检索数据。
7. 长耗时 AI 操作一律使用异步任务。
8. AI 输出必须先转化为结构化数据，再进入文档生成。
9. 模块之间保持松耦合。
10. 外部服务提供商必须可通过配置替换。

---

## 3. 系统边界

### 3.1 前端边界

前端负责：页面渲染、导航、表单、文件选择、前端校验、API 请求、服务端状态展示、任务进度展示、AI 结果预览、用户编辑、文档下载，以及 loading / empty / error / success 四种界面状态。

前端禁止做（权威清单）：

- OCR
- 视频抽帧
- 语音识别
- RAG 检索
- 向量索引
- LLM 推理
- Vision 推理
- Word 文档生成
- 权威权限判断
- 直接访问数据库

### 3.2 后端边界

后端负责：认证（authentication）、授权（authorization）、业务校验、数据库访问、文件存储、AI 编排、OCR、视觉分析、语音识别、RAG、文档生成、异步任务管理、审计日志、后端错误处理。

后端是系统的权威边界。前端校验只改善用户体验，不能替代后端校验。

### 3.3 AI 边界

AI 组件只提供建议与结构化抽取结果。AI 生成的内容不得直接成为最终检查文档。

固定流程：

`AI 生成 → 结构化草稿 → 用户审阅 → 用户修改 → 最终文档`

---

## 4. 技术架构

### 4.1 前端

本文档**不钉死前端框架**。前端技术栈由模型在首次实现时按以下选型原则自行决定，并在 `frontend/README.md` 中记录最终选择与理由：

1. 使用当前主流、社区活跃、文档完善的方案；优先 TypeScript 严格模式。
2. 选型必须覆盖以下能力：组件化 UI、声明式路由、服务端状态管理（缓存 / 轮询 / 失效）、表单与校验、样式方案、构建与开发服务器。
3. 不依赖任何低代码 / 在线生成平台（如 Lovable、v0 等）的产物或运行时；全部源码必须在本仓库内可读、可维护。
4. 组件库与图标库可选，但不得以"引入整套模板"代替设计；页面结构必须来自 `specs/` 的功能规格。
5. 构建产物必须是静态资源或可独立部署的应用，与后端部署相互独立。

前端代码必须独立于具体 AI 提供商。

### 4.2 后端

后端技术栈：

- Node.js（LTS 版本）
- TypeScript（strict 模式）
- HTTP 框架：由实现时选定（如 NestJS / Hono / Fastify），但必须支撑 §7 的分层架构与依赖注入能力
- ORM 与 migration 工具：由实现时选定（如 Drizzle / Prisma / TypeORM），schema 变更一律走 migration（见 `DATABASE.md`）
- PostgreSQL

异步处理：轻量任务可用进程内任务执行器；生产负载使用基于 Redis 的任务队列（如 BullMQ 或配置的其他任务系统）。长耗时的视频与文档任务不得阻塞正常 HTTP 请求。

### 4.3 AI 服务

AI 能力一律通过后端服务抽象访问，走 OpenAI 兼容 API。能力分类：language model（Qwen / DeepSeek / GPT 等）、vision model、OCR engine、speech recognition、embedding model、reranker、retrieval service。

具体模型名称与提供商必须来自配置，不得写死在业务代码中。

### 4.4 存储

存储分为三类。

关系数据库（PostgreSQL）保存：用户、权限、检查记录、拍照报告、询问记录、AI 任务状态、文件元数据、知识文档元数据、生成文档元数据、审计日志。

对象存储（Supabase Storage、S3 兼容存储或本地存储）保存：上传的视频 / 图片 / 音频、源文档、生成的 Word / PDF 文档、抽取的关键帧、临时处理文件。

向量数据库（默认 Chroma，或经配置替换的其他向量存储；Embedding 模型与提供商一律来自配置，见 §4.3）保存：文档 chunk 向量、chunk 元数据、来源引用、检索标识。向量数据库不得被当作主业务数据库使用。

---

## 5. 高层模块

平台划分为 14 个业务模块，每个模块应有清晰边界：

`Authentication`、`User Management`、`Dashboard`、`Fire Regulation QA`、`Inspection Record`、`Photo Report`、`Interview Record`、`Knowledge Base`、`File Management`、`AI Task Management`、`Document Generation`、`Statistics`、`Audit Logging`、`System Settings`

---

## 6. 前端架构

前端架构以**能力分层**定义，不绑定具体框架。无论最终选择哪个框架，代码组织必须能清晰映射到以下层次：

```text
Pages / Routes
  |
  v
Components
  |
  v
State Logic（状态逻辑层）
  |
  v
API Services
  |
  v
Central API Client
```

### 6.1 Pages / Routes

页面负责页面布局、功能组件组合、路由级状态与结果展示。页面中不应堆积大量 API 调用或数据转换逻辑。

必须覆盖的页面集合以 `specs/` 各功能规格为唯一定义来源（当前包括：登录与注册、Dashboard（含统计）、法规问答、检查记录、拍照报告、询问笔录、知识库、任务中心、设置）；新增或合并页面时先修改对应规格，本节不另行枚举。

### 6.2 Components

组件负责可复用的 UI 行为。必须具备的组件能力（命名与拆分由实现决定）：`FileUploader`、`TaskProgress`、`BackendStatus`、`ResultPreview`、`SourceCitation`、`DocumentDownloadButton`、`EditableField`、`EmptyState`、`ErrorState`。

避免创建职责几乎相同的多个组件。

### 6.3 状态管理

状态逻辑层（hooks / composables / stores，命名按所选框架惯例）封装可复用的 UI 状态与服务端状态行为。服务端状态（后端数据、任务进度、缓存与轮询）必须由统一的异步状态方案管理；本地组件状态只管理临时 UI 状态。任务轮询规则见 §9.2。

### 6.4 API Services

API service 定义对后端 REST API 的调用，按业务模块划分（认证、健康检查、法规问答、检查记录、拍照报告、询问笔录、知识库、任务、统计）。

页面与组件中不得直接发起 HTTP 请求，统一经由唯一的中央 API client；API Base URL 必须来自构建时注入的环境变量。

### 6.5 前端目录结构

目录结构由实现时按所选框架惯例自行设计，但必须满足：

- 上述五个层次各有明确归属，职责不混淆。
- 共享类型集中存放，避免类型散落在组件中。
- 一个业务模块一个 API service 文件。
- 结构在 `frontend/README.md` 中说明。

---

## 7. 后端架构

后端采用分层架构：

```text
Router
  |
  v
Application Service
  |
  +--------------------+
  |                    |
  v                    v
Repository          AI Service
  |                    |
  v                    v
Database           External Models
```

### 7.1 Routers

Router 负责：接收 HTTP 请求、解析请求参数、应用依赖注入、调用 application service、返回 API 响应。

Router 必须保持薄，不得包含：大段 AI prompt、直接模型调用、冗长的文档生成逻辑、复杂的数据库工作流。

### 7.2 Application Services

Application service 实现业务工作流，代表性 service：`InspectionRecordService`、`PhotoReportService`、`InterviewRecordService`、`KnowledgeBaseService`、`DocumentGenerationService`、`TaskService`。

Application service 负责协调：数据库操作、AI service、存储 service、任务执行、文档渲染。

### 7.3 Repositories

Repository 封装数据库访问，负责查询、插入、更新、事务感知的持久化。业务规则不得藏在 repository 中。

### 7.4 AI Services

AI service 按能力划分：`LLMService`、`VisionService`、`OCRService`、`SpeechService`、`EmbeddingService`、`RerankerService`、`RetrievalService`。由 application service 编排这些能力 service。

### 7.5 Storage Services

存储访问必须使用抽象层：

```text
StorageService
  |
  +-- LocalStorageProvider
  +-- SupabaseStorageProvider
  +-- S3StorageProvider
```

业务模块不得直接依赖某一个存储提供商。

### 7.6 后端目标目录结构

`backend/` 尚未实现，以下为 Node.js + TypeScript 目标结构（具体框架选定后可微调，但分层职责必须保留）：

```text
backend/
├── src/
│   ├── main.ts               # 进程入口
│   ├── app.ts                # HTTP 应用组装
│   ├── config/               # 统一配置加载（环境变量）
│   ├── common/               # 错误、日志、中间件、守卫
│   ├── modules/              # 业务模块：router/controller + service + repository
│   │   ├── auth/
│   │   ├── inspection-record/
│   │   ├── photo-report/
│   │   ├── interview-record/
│   │   ├── knowledge/
│   │   ├── tasks/
│   │   └── statistics/
│   ├── services/
│   │   ├── ai/               # LLM / Vision / OCR / Speech / Embedding / Reranker
│   │   ├── storage/          # 对象存储抽象
│   │   ├── documents/        # 文档模板渲染
│   │   └── tasks/            # 任务队列与执行器
│   ├── rag/
│   │   ├── parsers/
│   │   ├── chunking/
│   │   ├── embedding/
│   │   ├── retrieval/
│   │   └── reranking/
│   └── utils/
├── migrations/               # 数据库 migration（工具由实现选定）
├── data/
│   ├── templates/            # Word 模板
│   └── temporary/
├── tests/
└── package.json
```

---

## 8. API 架构

前端通过 REST API 与后端通信。默认 API 前缀：

```text
/api
```

目标 API 模块（与 `API.md` 对应）：

`/api/auth`、`/api/qa`、`/api/inspection-record`、`/api/photo-report`、`/api/interview-record`、`/api/knowledge`、`/api/tasks`、`/api/statistics`、`/api/files`

接口细节以 `API.md` 为准。

### 8.1 标准请求流

`Frontend Component → State Hook → Frontend API Service → HTTP Router → Application Service → Database / AI / Storage`

### 8.2 标准错误流

`后端异常 → Application Exception → Global Exception Handler → 标准 API 错误 → Frontend API Client → 可读的 UI 错误`

统一错误格式见 `API.md`。不得向普通用户暴露后端堆栈信息。

---

## 9. 异步任务架构

以下操作可能需要异步执行：视频抽帧、视觉分析、OCR、语音转写、知识库索引、大文档解析、Word 文档生成、PDF 转换、批量报告生成。

任务流：

`前端上传 → POST 生成接口 → 创建业务草稿 → 创建 AI 任务 → 返回 task_id → 后台 Worker 执行 → 更新进度 → 保存结构化结果 → 前端轮询 → 预览与审阅`

### 9.1 任务状态

任务状态枚举见 `DATABASE.md` 的 `ai_tasks` 表。

任务记录应包含：任务类型、当前状态、进度、当前阶段、结果引用、错误码、错误信息、创建时间、开始时间、完成时间。

### 9.2 任务轮询

前端通过以下接口轮询：

```text
GET /api/tasks/{task_id}
```

轮询要求：使用合理间隔；任务完成 / 失败 / 取消后停止；容忍临时网络错误；避免重复轮询请求。

未来版本可引入 Server-Sent Events / WebSocket / 推送通知；轮询仍是初始默认实现。

---

## 10. RAG 架构

RAG 子系统分为索引管线与查询管线。

### 10.1 索引管线

`源文档 → 文件解析 → 文档规范化 → 语义切分（chunking） → 元数据增强 → Embedding → 向量数据库`

chunk 必须保留的元数据清单以 `specs/knowledge-base.md`「字段清单（chunk 元数据）」为唯一定义，本文不重复列举。

### 10.2 查询管线

`用户问题 → Query 规范化 → Retriever → 候选 chunks → Reranker → 上下文构建 → LLM → 答案与引用`

法规问答应尽可能附带可追溯的证据。系统必须区分：检索到的事实、模型生成的解读、无可用证据。

---

## 11. 检查记录管线

`上传视频 → 创建 AI 任务 → 抽取音频与帧 →（语音识别 ∥ 视觉分析）→ OCR → 结构化抽取 → 检查记录草稿 → 用户审阅 → 模板渲染 → DOCX / PDF 输出`

结构化检查记录必须先入库，再进入文档渲染。

---

## 12. 拍照报告管线

`上传视频 → 创建 AI 任务 → 抽取候选帧 → 帧去重 → 视觉分析 → 地址与隐患抽取 → 选取关键帧 → 可编辑说明文字 → 模板渲染 → 拍照报告`

用户必须能够：删除识别错误的帧、调整帧顺序、编辑描述文字、核对识别出的地址、核对隐患信息。

---

## 13. 询问记录管线

`上传音频 → 语音识别 → 转写文本清洗 → 说话人分离 → 结构化抽取 → 询问记录草稿 → 用户审阅 → 模板渲染`

原始转写文本与结构化记录必须分开保存。

---

## 14. 文档生成架构

文档必须由结构化业务数据生成：

`数据库记录 → 模板数据映射 → 模板渲染 → 生成 DOCX → 可选 PDF 转换 → 对象存储 → 生成文档元数据入库`

Word 模板存放于：

```text
backend/data/templates/
```

不得直接用不受控的自由文本模型输出生成文档。

---

## 15. 文件架构

上传文件处理流：

`客户端文件 → 前端校验 → 后端校验 → 对象存储 → 文件元数据记录 → 处理任务`

临时文件必须与永久文件分开存放。推荐目录分类：

```text
uploads/
temporary/
key-frames/
knowledge/
templates/
generated/
```

临时处理文件应自动清理。

---

## 16. 数据库架构

PostgreSQL 保存结构化业务数据，主要数据库域：`Identity`、`Inspection`、`Photo Report`、`Interview Record`、`File Metadata`、`Generated Documents`、`AI Tasks`、`Knowledge Base Metadata`、`Audit Logs`。

表结构与枚举见 `DATABASE.md`。

数据库不得保存大文件二进制，除非有明确要求。

---

## 17. 认证与授权

认证（authentication）确认当前用户身份；授权（authorization）判断用户是否允许执行某个操作。

认证方案：自建 email/password 注册登录 + 密码哈希存储 + JWT Bearer Token，接口契约见 `API.md`。

角色定义见 `DATABASE.md`。

授权必须在后端强制执行；前端路由守卫只是界面层措施。

授权流：

```text
Request
  |
  v
Authentication Dependency
  |
  v
Current User
  |
  v
Permission Check
  |
  v
Application Service
```

---

## 18. 工程规范

### 18.1 审计

关键操作必须生成审计记录：登录、文件上传、记录创建、AI 文档生成、用户修改 AI 结果、记录定稿、知识文档删除、文档下载、权限变更。审计日志尽量 append-only；不得写入密钥或完整敏感文档内容。

### 18.2 配置

配置全部来自环境变量或安全配置中心，经后端统一的 settings 模块加载。禁止在业务代码中散落读取环境变量；禁止硬编码密钥。

### 18.3 外部服务抽象

LLM、OCR、语音识别、embedding、reranker、对象存储、向量数据库一律通过内部接口访问。更换提供商不得要求重写业务工作流。

### 18.4 安全

业务 API 必须认证；授权在后端校验；上传文件校验类型 / 大小 / MIME；使用安全的存储文件名；下载 URL 需签名或受保护；限制 CORS；必要时限流；输入校验、输出转义；数据库最小权限访问。永不信任：前端校验结果、上传文件名、客户端提供的 MIME 类型、客户端提供的用户 ID、AI 生成的法律结论。

### 18.5 可观测性

后端使用结构化日志，建议字段：`timestamp`、`level`、`request_id`、`user_id`、`task_id`、`module`、`operation`、`duration`、`status`、`error_code`。不记录：密码、访问令牌、API key、完整敏感文档、非必要的模型输入输出。关注指标：API 响应时间、任务处理时长、任务失败率、模型请求失败率、知识索引失败率、存储失败率、数据库连接失败。提供健康检查接口 `/health`。

### 18.6 部署

开发环境：浏览器 → 前端 dev server → 本地 Node.js 后端 → 本地 PostgreSQL / 对象存储 / 向量数据库 / AI 服务。生产环境：浏览器 → CDN → 反向代理 / API 网关 → Node.js 后端 → PostgreSQL / 对象存储 / 向量数据库 / Redis 任务队列 / 后台 Worker / 外部 AI 提供商；容器化部署。前后端部署保持相互独立。

### 18.7 扩展性

初期可作为单个 Node.js 应用运行；负载增长后再拆分 API Server / AI Worker / Video Worker / Document Worker / Knowledge Index Worker / Scheduler。在确有需要之前不引入分布式复杂度；保持模块边界干净以便未来拆分。

### 18.8 可靠性

需处理：网络超时、提供商故障、模型限流、非法 AI 输出、上传中断、Worker 重启、任务重复提交、文档生成失败、管线部分失败。长耗时任务尽量幂等；重试任务不得静默产生重复的最终记录。

### 18.9 测试

测试分层：unit（工具函数、schema 校验、解析器、数据映射、字段格式化、任务状态流转）、integration（API 与数据库、存储、任务执行、RAG 检索、文档生成）、e2e（登录、上传、任务进度、结果审阅、记录更新、文档下载）。自动化测试中外部 AI 提供商必须可 mock。

---

## 19. 架构约束

以下约束必须始终遵守：

1. 前端禁止任何 AI 推理。
2. 前端禁止直接访问业务数据库。
3. 业务逻辑中禁止硬编码模型名称。
4. 禁止硬编码密钥。
5. 禁止在普通数据库字段中存放大文件二进制。
6. 禁止业务记录只存在于生成的 Word 文件中。
7. RAG 启用时，禁止不经检索的法规问答。
8. 禁止未经用户审阅就将 AI 文档定稿。
9. 禁止没有 migration 的 schema 变更。
10. 前端禁止依赖任何低代码 / 在线生成平台的产物、运行时或锁定文件；前端源码必须由模型依据本文档与 `specs/` 生成。
