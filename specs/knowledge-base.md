# Knowledge Base（知识库）

## 目的与范围

知识库管理 RAG 使用的来源文档：使解析与索引状态可见、防止静默重复，并保持关系元数据、对象存储与向量索引三者同步。

范围（v1）：列出有权限的知识文档、逐个上传受支持文档、跟踪解析与索引状态、展示文档元数据与失败原因、确认后删除文档、触发全量索引重建、查看知识库聚合计数、变更后刷新列表。

范围外：浏览器内文档编辑、目录层级、协作批注、自动网页抓取、表格（XLSX）索引、文档级共享流程、手工编辑 chunk。

## 角色与权限

通用规则见 specs/_common.md。本功能最低角色：上传、删除、重建为 `admin`；`supervisor` 经明确授权可管理内容；`inspector` 只读查看状态；`viewer` 无管理权限。源文档访问与所有管理操作以后端权限校验为准。

## 功能要求

### 文档列表

- 列表展示：`title`、`document_type`、`version`、`issuing_authority`、`effective_date` / `expiration_date`、索引状态、`chunk_count`、`updated_at`，失败时附安全摘要。
- 支持刷新与按 `status` 过滤（查询参数见 API.md）。

### 上传

- 使用文件类别：文档类（`.pdf` / `.doc` / `.docx` / `.ppt` / `.pptx` / `.txt` / `.md`）；白名单与大小上限见 API.md §9。
- 上传前展示文件名与大小；上传进度与索引进度分开展示。
- 后端要求的元数据（标题等）必须采集或提取；`effective_date` 不得晚于 `expiration_date`。
- 加密或损坏的不受支持文件必须返回特定可读错误。
- 后端确认索引完成前，UI 不得显示 `indexed`。

### 索引状态

- 文档状态机（取值定义权在 DATABASE.md `knowledge_documents.status`）：`uploaded` → `parsing` → `indexing` → `indexed`；异常态 `failed`；失效态 `outdated`。
- 索引管线：`校验并存储 → Parse → Normalize → Semantic Chunking → 元数据补全 → Embedding → 向量索引 → 标记 indexed`；各环节职责独立，RAG 通用流程约束见 AGENTS.md。
- 状态不得仅依赖颜色表达；`failed` 必须展示安全、可操作的失败原因。
- 索引与重建均为异步任务（`task_type` 分别为 `knowledge_indexing` / `knowledge_reindexing`），轮询协议见 specs/_common.md。

### 删除

- 删除须显式确认并展示文档标题。
- 后端必须协同完成：关系元数据软删除、源文件生命周期处理、向量索引移除。
- 后端确认前 UI 不得永久移除该行；部分删除失败必须保持可见以便恢复。

### 重建

- 全量重建须确认（代价高且可能暂时影响检索）。
- 同一时刻只允许一个等效重建任务；进度与失败详情必须可见。
- 重建不得产生重复的生效 chunk。

## 业务规则（本功能独有）

- 原始源文档是重建检索数据的权威输入；向量库只存派生的 chunk 与 embedding，不是主业务记录。
- 重复内容按 `checksum` 检测；无显式版本规则时，新版本不得静默替换现版本。
- 生效、过期、被取代、`outdated` 的文档必须可区分。
- 已删除或无权限的文档不得再被检索到；检索必须在内容进入 AI 模型前完成文档权限校验。
- 索引成功要求全部必需元数据与向量条目一致提交；必需阶段失败时不得将文档标记为 `indexed`。
- 重建必须可恢复：失败的重建不得静默破坏最后可用的索引。
- RAG 答案必须保留对文档元数据的可追溯引用。
- 文档全文、embedding 不得下发前端；上传文档按不可信内容在受限环境中解析；响应与日志不得暴露向量标识符与原始 parser 错误堆栈。

## 字段清单（chunk 元数据）

索引管线必须为每个 chunk 保留以下可获得的元数据（本清单为全仓库唯一定义处，不得删减）：

- 文档 ID 与标题；
- 文档类型（`document_type`）与版本（`version`）；
- 页码（page number）；
- 章 / 节 / 条（chapter / section / article）；
- 生效日期（`effective_date`）与发布机构（`issuing_authority`）；
- 来源引用（source reference）。

## UI 结构

页面按 `页头与知识库聚合计数 → 上传与重建操作 → 过滤器 → 文档表格/卡片 → 状态与错误详情` 组织。文件选择器或拖拽区须可访问；删除与重建使用确认对话框；请求进行中禁用重复操作；状态展示与破坏性操作可键盘使用；面向用户的文案为中文且错误可操作。

## API 端点

- `GET /api/knowledge/documents` — 文档列表（分页、按 `status` 过滤）
- `POST /api/knowledge/documents` — 上传源文档（`FormData`，返回异步索引任务）
- `DELETE /api/knowledge/documents/{id}` — 删除文档并移除其索引数据
- `POST /api/knowledge/rebuild` — 全量重建索引（异步任务）
- `GET /api/knowledge/status` — 知识库聚合计数（文档总数及各状态计数）
- `GET /api/tasks/{task_id}` — 任务轮询（协议见 specs/_common.md）

请求/响应 schema 见 API.md，本文不复制。

## 数据影响

涉及表：`knowledge_documents`（源元数据与当前索引状态）、`knowledge_index_jobs`（索引操作与结果）、`uploaded_files`（源文件元数据）、`ai_tasks`（索引与重建异步任务）、`audit_logs`（上传、删除、重建审计）；表结构定义权在 DATABASE.md。向量库存放 chunk、embedding 与来源引用；对象存储存放原始文档。

## 验收标准

- [ ] 授权用户可列出知识文档并看到准确状态；知识库聚合计数与列表一致。
- [ ] 合法文档可上传，且不会被提前标记为 `indexed`。
- [ ] 解析、分块、embedding、索引产出可追溯的来源元数据（chunk 元数据字段齐全）。
- [ ] 重复内容按 checksum 检测，或经显式版本规则处理。
- [ ] 索引失败展示可操作错误，且不静默产生半成品的生效索引。
- [ ] 删除文档后不再被检索到，源文件与向量索引清理安全可靠。
- [ ] 全量重建报告进度，不产生重复的生效 chunk，失败时可恢复到最后可用索引。
- [ ] 空、加载中、各索引状态与后端错误状态可区分；通用验收标准见 specs/_common.md。
