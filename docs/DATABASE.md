# DATABASE.md

# 数据库设计

本文档是 Fire Intelligence Platform 数据库表结构与枚举的唯一权威文件，描述数据库结构、表关系、约束与数据归属规则。

数据库是业务数据的事实来源（source of truth）。AI 生成的中间文件与向量嵌入不能替代结构化业务记录。

# 数据库技术

- 关系数据库：PostgreSQL
- ORM：SQLAlchemy
- Schema 校验：Pydantic
- Migration 工具：Alembic
- 文件存储：Supabase Storage、S3 兼容对象存储、本地存储（仅限开发环境）
- 向量数据库：Chroma 或其他已配置的向量存储

向量数据库仅保存检索数据，业务数据必须保留在 PostgreSQL 中。

# 设计原则

- 使用 UUID 主键。
- 时间戳统一存储为 UTC。
- 表间关系使用外键。
- 避免存储重复的业务数据。
- 需要恢复或审计的记录使用软删除。
- AI 任务记录与最终业务文档分开保存。
- 大文件存入对象存储，不直接存入数据库列。
- 数据库中保存文件元数据与存储路径。
- 每次 schema 变更都必须包含 Alembic migration，禁止绕过 migration 手工修改表结构。
- 已应用到共享环境的 migration 不得编辑，应创建新的修正 migration。

# 命名规范

表名使用复数 snake_case（如 `users`、`inspection_records`、`photo_reports`、`knowledge_documents`、`ai_tasks`）；列名使用 snake_case（如 `created_at`、`updated_at`、`storage_path`、`task_status`）；外键使用被引用实体名加 `_id` 后缀（如 `user_id`、`inspection_record_id`、`task_id`）。

# 通用字段

大多数业务表应包含以下字段：

```text
id          UUID        主键
created_at  TIMESTAMP   创建时间
updated_at  TIMESTAMP   最后更新时间
created_by  UUID        创建记录的用户
deleted_at  TIMESTAMP   软删除时间
```

`deleted_at` 可为空；非空表示该记录已被软删除。

# 核心实体

数据库设计包含以下核心实体：

- users
- user_profiles
- inspection_records
- inspection_record_items
- photo_reports
- photo_report_images
- interview_records
- uploaded_files
- generated_documents
- ai_tasks
- knowledge_documents
- knowledge_index_jobs
- audit_logs

# 实体关系

```text
users
  |
  +-- user_profiles
  |
  +-- inspection_records
  |     |
  |     +-- inspection_record_items
  |     +-- uploaded_files
  |     +-- generated_documents
  |
  +-- photo_reports
  |     |
  |     +-- photo_report_images
  |     +-- uploaded_files
  |     +-- generated_documents
  |
  +-- interview_records
  |     |
  |     +-- uploaded_files
  |     +-- generated_documents
  |
  +-- knowledge_documents
  |
  +-- ai_tasks
  |
  +-- audit_logs
```

# 表：users

存储用户认证信息。

认证方案为自建 email/password：密码经强哈希算法（如 bcrypt）哈希后存储于 `users.password_hash`，绝不存储明文密码；API 认证使用 Bearer token（见 API.md）。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| email | VARCHAR | 是 | 用户邮箱 |
| password_hash | VARCHAR | 是 | 密码哈希（如 bcrypt） |
| username | VARCHAR | 否 | 显示用户名 |
| role | VARCHAR | 是 | 用户角色 |
| is_active | BOOLEAN | 是 | 账号是否启用 |
| last_login_at | TIMESTAMP | 否 | 最近登录时间 |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |
| deleted_at | TIMESTAMP | 否 | 软删除时间 |

## Role 取值

```text
admin
supervisor
inspector
viewer
```

## 约束

- `email` 必须唯一。
- `role` 必须使用批准的取值。
- 已删除用户不应出现在普通查询结果中。

# 表：user_profiles

存储与认证数据分离的用户资料信息。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| user_id | UUID | 是 | 引用 users.id |
| full_name | VARCHAR | 否 | 姓名 |
| department | VARCHAR | 否 | 部门 |
| position | VARCHAR | 否 | 职位 |
| phone | VARCHAR | 否 | 电话号码 |
| avatar_path | VARCHAR | 否 | 头像存储路径 |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |

## 约束

- `user_id` 必须唯一。
- 一个用户至多拥有一条 profile。

# 表：inspection_records

存储消防检查记录文档。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| record_number | VARCHAR | 否 | 业务记录编号 |
| title | VARCHAR | 否 | 记录标题 |
| inspection_unit | VARCHAR | 否 | 被检查单位 |
| inspection_address | VARCHAR | 否 | 检查地址 |
| inspection_date | TIMESTAMP | 否 | 检查日期 |
| inspector_names | JSONB | 否 | 检查人员姓名列表 |
| contact_person | VARCHAR | 否 | 联系人 |
| contact_phone | VARCHAR | 否 | 联系电话 |
| summary | TEXT | 否 | 检查总结 |
| conclusion | TEXT | 否 | 检查结论 |
| status | VARCHAR | 是 | 记录状态 |
| source_task_id | UUID | 否 | 生成该记录的 AI 任务 |
| created_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |
| deleted_at | TIMESTAMP | 否 | 软删除时间 |

## Status 取值

```text
draft
processing
generated
reviewed
finalized
archived
failed
```

## 约束

- `record_number` 存在时应唯一。
- 已定稿（finalized）的记录不得被静默覆盖。
- AI 生成的内容在定稿前必须保持可编辑。

# 表：inspection_record_items

存储单条检查发现或违规项。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| inspection_record_id | UUID | 是 | 引用 inspection_records.id |
| item_type | VARCHAR | 是 | 发现项类型 |
| location | VARCHAR | 否 | 发现位置 |
| description | TEXT | 是 | 发现描述 |
| legal_basis | TEXT | 否 | 相关法律依据 |
| correction_requirement | TEXT | 否 | 整改要求 |
| severity | VARCHAR | 否 | 严重程度 |
| sort_order | INTEGER | 是 | 显示顺序 |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |

## Item Type 取值

```text
compliant
violation
hazard
observation
recommendation
```

## Severity 取值

```text
low
medium
high
critical
```

# 表：photo_reports

存储照片报告文档。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| title | VARCHAR | 否 | 报告标题 |
| inspection_unit | VARCHAR | 否 | 被检查单位 |
| inspection_address | VARCHAR | 否 | 检查地址 |
| violation_summary | TEXT | 否 | 违规情况摘要 |
| status | VARCHAR | 是 | 报告状态 |
| source_task_id | UUID | 否 | AI 生成任务 |
| created_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |
| deleted_at | TIMESTAMP | 否 | 软删除时间 |

## Status 取值

```text
draft
processing
generated
reviewed
finalized
archived
failed
```

# 表：photo_report_images

存储照片报告中包含的图片及其说明。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| photo_report_id | UUID | 是 | 引用 photo_reports.id |
| uploaded_file_id | UUID | 是 | 引用 uploaded_files.id |
| frame_timestamp | FLOAT | 否 | 源视频时间戳（秒） |
| caption | TEXT | 否 | 可编辑的图片说明 |
| detected_address | VARCHAR | 否 | 从图片识别的地址 |
| detected_violation | TEXT | 否 | 从图片识别的违规行为 |
| is_selected | BOOLEAN | 是 | 是否纳入最终文档 |
| sort_order | INTEGER | 是 | 显示顺序 |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |

## 约束

- 图片说明必须保持可编辑。
- 一个照片报告可包含多张图片。
- 从报告中移除图片不应必然删除原始文件。

# 表：interview_records

存储询问记录（interview record）文档。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| title | VARCHAR | 否 | 记录标题 |
| interviewee_name | VARCHAR | 否 | 被访谈人 |
| interviewer_names | JSONB | 否 | 访谈人列表 |
| location | VARCHAR | 否 | 访谈地点 |
| started_at | TIMESTAMP | 否 | 开始时间 |
| ended_at | TIMESTAMP | 否 | 结束时间 |
| transcript | TEXT | 否 | 语音转写文本 |
| structured_content | JSONB | 否 | 结构化访谈内容 |
| status | VARCHAR | 是 | 记录状态 |
| source_task_id | UUID | 否 | AI 任务 |
| created_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |
| deleted_at | TIMESTAMP | 否 | 软删除时间 |

## Status 取值

```text
draft
processing
generated
reviewed
finalized
archived
failed
```

# 表：uploaded_files

存储上传文件的元数据。文件本体应存入对象存储。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| original_name | VARCHAR | 是 | 原始文件名 |
| storage_path | VARCHAR | 是 | 对象存储路径 |
| storage_provider | VARCHAR | 是 | 存储提供商 |
| mime_type | VARCHAR | 否 | MIME 类型 |
| file_extension | VARCHAR | 否 | 文件扩展名 |
| size_bytes | BIGINT | 是 | 文件大小（字节） |
| checksum | VARCHAR | 否 | 文件校验和 |
| category | VARCHAR | 是 | 文件类别 |
| uploaded_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 上传时间 |
| deleted_at | TIMESTAMP | 否 | 软删除时间 |

## Category 取值

```text
video
image
audio
document
template
generated_document
knowledge_source
```

## 约束

- 不得在本表直接存储文件二进制数据。
- 存储路径应尽量保持唯一。
- 处理前必须校验文件类型与大小。

# 表：generated_documents

存储生成的 Word、PDF 或其他输出文档。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| document_type | VARCHAR | 是 | 文档类型 |
| source_entity_type | VARCHAR | 是 | 来源业务实体类型 |
| source_entity_id | UUID | 是 | 来源业务实体 ID |
| uploaded_file_id | UUID | 是 | 引用 uploaded_files.id |
| version | INTEGER | 是 | 文档版本 |
| generated_by_task_id | UUID | 否 | 引用 ai_tasks.id |
| created_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 创建时间 |

## Document Type 取值

```text
inspection_record_docx
photo_report_docx
interview_record_docx
inspection_record_pdf
photo_report_pdf
interview_record_pdf
```

## 约束

- 不得覆盖已定稿的历史文档版本。
- 重新生成已定稿文档时递增 `version`。
- 按要求保留下载历史。

# 表：ai_tasks

存储异步 AI 处理任务。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| task_type | VARCHAR | 是 | 任务类别 |
| status | VARCHAR | 是 | 任务状态 |
| progress | INTEGER | 是 | 进度（0 到 100） |
| current_stage | VARCHAR | 否 | 当前处理阶段 |
| input_data | JSONB | 否 | 非敏感任务输入元数据 |
| result_data | JSONB | 否 | 结构化 AI 结果 |
| error_code | VARCHAR | 否 | 机器可读错误码 |
| error_message | TEXT | 否 | 可读错误信息 |
| started_at | TIMESTAMP | 否 | 任务开始时间 |
| completed_at | TIMESTAMP | 否 | 任务完成时间 |
| created_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |

## Status 取值

```text
pending
queued
processing
completed
failed
cancelled
```

## Task Type 取值

```text
inspection_record_generation
photo_report_generation
interview_record_generation
speech_transcription
video_analysis
document_generation
knowledge_indexing
knowledge_reindexing
```

## 约束

- `progress` 必须在 0 到 100 之间。
- 已完成任务应具有 `completed_at`。
- 失败任务应具有 `error_message`。
- 敏感文件内容不得复制到 `input_data`。

# 表：knowledge_documents

存储知识库使用的来源文档。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| title | VARCHAR | 是 | 文档标题 |
| document_type | VARCHAR | 否 | 来源文档类型 |
| uploaded_file_id | UUID | 是 | 引用 uploaded_files.id |
| status | VARCHAR | 是 | 索引状态 |
| version | VARCHAR | 否 | 文档版本 |
| issuing_authority | VARCHAR | 否 | 发布机构 |
| effective_date | DATE | 否 | 生效日期 |
| expiration_date | DATE | 否 | 失效日期 |
| chunk_count | INTEGER | 否 | 已索引分块数量 |
| checksum | VARCHAR | 否 | 内容校验和 |
| doc_metadata | JSONB | 否 | 附加文档元数据 |
| created_by | UUID | 是 | 引用 users.id |
| created_at | TIMESTAMP | 是 | 创建时间 |
| updated_at | TIMESTAMP | 是 | 最后更新时间 |
| deleted_at | TIMESTAMP | 否 | 软删除时间 |

## Status 取值

```text
uploaded
parsing
indexing
indexed
failed
outdated
```

## 约束

- 应尽量使用 `checksum` 检测重复文档。
- 重建索引不得静默产生重复的生效版本。
- 删除知识文档时必须同时从向量索引中移除。
- 列名使用 `doc_metadata` 而非 `metadata`，以避免与 SQLAlchemy Declarative 的保留属性名 `metadata` 冲突。

# 表：knowledge_index_jobs

存储知识库索引任务。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| knowledge_document_id | UUID | 否 | 引用 knowledge_documents.id |
| ai_task_id | UUID | 否 | 引用 ai_tasks.id |
| action | VARCHAR | 是 | 索引操作 |
| status | VARCHAR | 是 | 任务状态 |
| indexed_chunks | INTEGER | 否 | 已索引分块数 |
| error_message | TEXT | 否 | 错误信息 |
| created_at | TIMESTAMP | 是 | 创建时间 |
| completed_at | TIMESTAMP | 否 | 完成时间 |

## Action 取值

```text
index
reindex
delete_index
full_rebuild
```

# 表：audit_logs

存储重要的用户与系统操作。

## 列

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| user_id | UUID | 否 | 引用 users.id |
| action | VARCHAR | 是 | 操作名称 |
| entity_type | VARCHAR | 否 | 目标实体类型 |
| entity_id | UUID | 否 | 目标实体 ID |
| request_id | VARCHAR | 否 | 请求追踪 ID |
| ip_address | VARCHAR | 否 | 请求 IP |
| details | JSONB | 否 | 安全的操作元数据 |
| created_at | TIMESTAMP | 是 | 创建时间 |

## 操作示例

```text
user.login
inspection_record.create
inspection_record.finalize
photo_report.generate
knowledge_document.upload
knowledge_document.delete
document.download
```

## 约束

- 审计日志通常只允许追加。
- 不得存储密码、token 或完整的敏感文档内容。
- 审计日志的访问应受到限制。

# 可选表

以下表可在需要时增加：

- inspection_units
- model_configurations
- prompt_versions
- evaluation_results
- notifications

企业管理的 `organizations` / `departments` / `permissions` / `role_permissions` 已在 Milestone 6 落地为核心表,定义见下方。其余表在对应功能被需要之前不要创建。

# 表：organizations（Milestone 6）

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| name | VARCHAR | 是 | 组织名称 |
| code | VARCHAR | 是 | 组织编码,唯一 |
| description | VARCHAR | 否 | 描述 |
| created_at / updated_at / deleted_at | TIMESTAMP | - | 通用字段 |

# 表：departments（Milestone 6）

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| organization_id | UUID | 是 | 引用 organizations.id |
| name | VARCHAR | 是 | 部门名称 |
| parent_id | UUID | 否 | 上级部门(预留层级) |
| created_at / updated_at / deleted_at | TIMESTAMP | - | 通用字段 |

# 表：permissions / role_permissions（Milestone 6）

权限以角色(`users.role`)为基准,权限码通过 `role_permissions` 关联到角色。默认权限矩阵在 `app/services/permission_service.py` 维护(幂等种子)。

- `permissions`：`code`(唯一)、`name`、`description`。
- `role_permissions`：`role`(users.role 取值)、`permission_code`,联合唯一。

# 用户归属（Milestone 6）

`users` 表新增可空列：`organization_id`(引用 organizations.id)、`department_id`(引用 departments.id)。

统计范围规则：admin=system；supervisor=organization(按记录创建者所属组织过滤)；inspector/viewer=personal。未分配组织的 supervisor 默认查看全部。




# 表：prompt_versions（Milestone 8）

版本化 Prompt 目录,初始种子来自 `app/prompts/*.py`,管理员可编辑。

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| key | VARCHAR | 是 | 稳定标识(如 qa.QA_SYSTEM) |
| name / description | VARCHAR / TEXT | 否 | 展示信息 |
| content | TEXT | 是 | Prompt 文本 |
| version | INTEGER | 是 | 版本号,编辑时递增 |
| is_active | BOOLEAN | 是 | 是否生效(仅一个生效版本) |
| created_by | UUID | 否 | 编辑者 |

# 表：model_configurations（Milestone 8）

按能力类型配置的模型,模型路由优先使用生效配置,回退到环境变量。

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| name | VARCHAR | 是 | 配置名称 |
| kind | VARCHAR | 是 | llm / vision / ocr / speech / embedding / reranker |
| provider | VARCHAR | 是 | 提供商 |
| model_name | VARCHAR | 是 | 模型名 |
| base_url | VARCHAR | 否 | 覆盖 Base URL |
| api_key_ref | VARCHAR | 否 | 密钥环境变量名(不存密钥本身) |
| is_active / priority | BOOLEAN / INTEGER | 是 | 生效标记与优先级 |

# 表：evaluation_results（Milestone 8）

评估运行结果(真实调用 RAG+LLM 管线后按规则计分)。

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| name / status | VARCHAR | 是 | 评估名称与状态 |
| total_questions / passed | INTEGER | 是 | 问题总数与通过数 |
| details | JSONB | 否 | 逐题检查明细 |
| created_by | UUID | 否 | 运行者 |

# 表：plugins（Milestone 8）

服务端插件注册表。插件以 `app.plugins.builtin.*` 模块形式提供 PLUGIN 契约(名称/版本/钩子),在平台定义点执行。

| 列名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | UUID | 是 | 主键 |
| name | VARCHAR | 是 | 插件名,唯一 |
| version / description | VARCHAR / TEXT | 否 | 版本与说明 |
| entry_point | VARCHAR | 是 | 加载入口 |
| enabled | BOOLEAN | 是 | 是否启用 |

# MCP（Milestone 8）

MCP 服务器通过环境变量 `MCP_SERVERS`(JSON 数组)配置,客户端实现于 `app/mcp/client.py`(HTTP JSON-RPC),工具以 Agent 工具形式暴露。

# Agent（Milestone 8）

Agent 基于 OpenAI 兼容 function calling(`app/services/ai/agent.py`),内置工具:知识检索、统计摘要。多智能体编排由 AgentOrchestrator 实现,任务经规划器拆解执行。

# 索引

推荐索引：

```text
users.email
inspection_records.created_by
inspection_records.status
inspection_records.inspection_date
photo_reports.created_by
interview_records.created_by
uploaded_files.uploaded_by
uploaded_files.checksum
ai_tasks.status
ai_tasks.task_type
knowledge_documents.status
knowledge_documents.checksum
audit_logs.user_id
audit_logs.created_at
```

仅当查询模式确实需要时才使用复合索引，例如 `ai_tasks(created_by, status, created_at)`、`inspection_records(created_by, status, created_at)`。

# 数据归属

用户通常只能访问自己创建的记录或所属组织的记录；管理员可按照权限规则访问全部记录。鉴权必须由后端强制执行，前端可见性不是安全边界。

# 文件删除规则

删除业务记录不应立即移除共享的来源文件。推荐流程：

```text
业务记录被软删除
        ↓
检查文件引用
        ↓
标记无引用的文件待清理
        ↓
异步删除存储对象
```

仍被其他记录引用的存储文件不得删除。

# AI 数据规则

AI 输出应尽量以结构化数据保存（如 `result_data`、`structured_content`、`detected_violation`、`legal_basis`）。

不得仅依赖生成的 Word 文件作为业务记录：生成的文件是输出，结构化数据库记录才是事实来源。

# 事务规则

涉及多个相关写入的操作必须使用数据库事务，例如：

- 创建检查记录及其检查项。
- 创建照片报告及其报告图片。
- 定稿记录并创建生成文档。
- 删除知识文档并安排向量索引清理。

必要步骤失败时回滚整个操作。

# 安全规则

- 绝不存储明文密码（密码哈希存于 `users.password_hash`）。
- 不在业务表中存储 API key。
- 敏感数据按要求加密。
- 数据库凭据按环境隔离。
- 使用最小权限数据库账号。
- 在后端服务中强制鉴权。
- 避免在非必要场景暴露内部数据库 ID。
