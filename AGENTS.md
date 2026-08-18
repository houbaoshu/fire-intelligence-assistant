# AGENTS.md

本仓库是一个 AI 驱动的消防检查系统。本文件是全仓库的编码规则权威文件。

## 现状说明

- frontend/ 尚未实现：必须由模型依据 docs/ARCHITECTURE.md §4.1/§6 与 specs/ 从零选型并生成，禁止复制外部脚手架或低代码平台产物。
- backend/ 尚未实现：按 docs/ARCHITECTURE.md §7 以 Node.js + TypeScript 实现。

动手前必须先理解权威文档定义的目标架构。

## 文档单一信息源

| 信息类别 | 权威文件 |
| --- | --- |
| 编码规则 | AGENTS.md（本文件） |
| 架构与目录结构 | docs/ARCHITECTURE.md |
| 数据库表与枚举 | docs/DATABASE.md |
| API 契约 | docs/API.md |
| AI 组件与工作流 | docs/AI_CONTEXT.md |
| 项目概述与环境变量 | docs/PROJECT.md |
| 里程碑 | docs/ROADMAP.md |
| 功能规格 | specs/ 目录 |
| 跨功能公共约定 | specs/_common.md |

规则：每类信息只在其权威文件中定义，其他文件必须引用而非复制。

## 核心原则（Core Principles）

写代码之前必须：

1. 阅读现有实现。
2. 复用现有模块。
3. 避免重复逻辑。
4. 保持改动聚焦。
5. 尽可能保持向后兼容。

除非明确要求，禁止重写项目的大段代码。

## 技术栈（Project Architecture）

技术栈见 docs/ARCHITECTURE.md。

## 架构职责（Architecture Responsibilities）

前后端职责划分见 docs/ARCHITECTURE.md。

禁止将 AI 逻辑移入前端。

## 目录职责（Folder Responsibilities）

前端（frontend/，框架由实现时按 ARCHITECTURE.md §4.1 选定）：

- 页面 / 路由：页面布局与功能组件组合。
- components/：可复用 UI。
- 状态逻辑层：可复用状态逻辑（hooks / composables / stores，按所选框架惯例）。
- services/：HTTP 请求（一个业务模块一个 service 文件）。
- lib/：工具函数。
- types/：共享 TypeScript 类型。

后端（backend/，Node.js + TypeScript）：

- modules/：按业务模块组织 HTTP 入口与业务逻辑（router/controller + service + repository）。
- services/ai/：AI 能力抽象。
- services/storage/：对象存储抽象。
- services/documents/：文档模板渲染。
- services/tasks/：任务队列与执行器。
- config/：统一配置加载。
- common/：错误、日志、中间件。
- rag/：知识库管线。
- data/templates/：Word 模板。

禁止混淆各目录的职责。

## API 规则

- 前端禁止硬编码 API 响应，必须始终调用后端 API。
- API Base URL 必须来自环境变量。
- 禁止硬编码 secrets。
- 禁止硬编码 tokens。

## AI 规则

职责划分：

- 大语言模型（LLM）生成文本。
- 视觉模型（Vision Models）理解图片与视频。
- OCR 提取文字。
- RAG 检索知识。
- Embedding 模型生成向量。

必须保持以上职责相互独立。

禁止实现假的 AI 逻辑。

## RAG 规则

知识检索必须遵循以下流程：

`Documents → Parsing → Chunking → Embedding → Vector Store → Retrieval → Reranking → LLM`

- 禁止跳过检索环节。
- RAG 启用时，禁止让 LLM 凭想象作答。

## Prompt 规则

- Prompt 禁止嵌入 UI 组件内部，必须单独存放。
- 保持 Prompt 可复用。
- 避免重复的 Prompt。

## 文书生成（Document Generation）

- Word 模板必须存放于 backend/data/templates/。
- 生成的文书由后端产出。
- 前端只负责：`Upload → Monitor progress → Preview → Download`。
- 禁止在前端生成 Word 文档。

## 视频处理（Video Processing）

- 视频处理属于后端职责，前端只上传文件。
- 后端执行：`Frame extraction → Vision analysis → OCR → LLM reasoning → Document generation`。

## 文件上传（File Upload）

- 必须校验：扩展名、文件大小。
- 必须显示上传进度。
- 必须显示可读的错误信息。
- 禁止静默忽略失败。

## TypeScript（前后端通用）

- 使用 strict 模式与严格类型。
- 避免使用 any。
- 删除未使用的 import。
- 保持构建干净。

## 后端（Node.js）

- 请求 / 响应必须使用 schema 校验（如 zod 或框架自带校验机制）。
- 保持 router/controller 轻薄。
- 业务逻辑必须放在 service 中。
- 依赖通过注入方式传递，禁止在业务代码中直接 new 外部服务客户端。

## 数据库（Database）

- 除非必要，禁止编写原生 SQL。
- 必须使用 ORM / 查询构建器访问数据库。
- 必须创建 migration；schema 变更一律走 migration。
- 禁止破坏现有 schema。

## 环境变量（Environment Variables）

- 配置必须从 .env 读取。
- 禁止硬编码：API Keys、Passwords、URLs、Secrets。

## 日志（Logging）

- 记录有用的信息。
- 禁止记录：密码、Token、敏感文档。

## UI

- 使用现有组件。
- 保持间距一致。
- 必须有 loading 状态、empty 状态、error 状态。
- 保持界面专业。
- 避免花哨的动画。

## 性能（Performance）

- 避免不必要的渲染与重复渲染。
- 大页面必须懒加载（lazy load）。
- 避免重复的 API 请求。

## 错误处理（Error Handling）

- 禁止吞掉异常。
- 返回可读的错误信息。
- 展示可操作的错误。

## 安全（Security）

- 必须校验所有上传的文件。
- 必须转义不可信内容。
- 禁止暴露后端 secrets。
- 禁止信任客户端输入。

## 测试（Testing）

任务完成前必须依次执行：Build → Lint → Type Check，并修复所有错误。

构建失败时，禁止声称任务成功。

## Git

- 提交小型、逻辑内聚的改动。
- 禁止重写已发布的历史。
- 避免 force push。
- 避免 rebase 已推送的提交。
- 保持仓库可构建。

## 代码风格（Code Style）

- 优先修改现有代码。
- 避免创建重复的组件。
- 优先组合（composition）而非复制。
- 保持函数短小。
- 保持文件聚焦。

## 决策优先级（Decision Priority）

实现功能时，按以下优先级决策：

1. 复用现有代码。
2. 遵循项目架构。
3. 保持代码简单。
4. 保持类型安全。
5. 保持模块独立。

## 执行流程（Execution）

接到开发任务时：

1. 理解现有实现。
2. 制定计划。
3. 增量实现。
4. 保持项目可构建。
5. 验证构建。
6. 说明重要改动。

不要做无关的重构。

不确定时，保留现有架构。
