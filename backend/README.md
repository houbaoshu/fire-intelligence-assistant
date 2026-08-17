# Fire Intelligence Platform — Backend

FastAPI 后端。Milestone 1：认证（注册/登录/me/refresh）、健康检查、存储抽象骨架。
Milestone 2：消防检查工作流 —— 文件上传四重校验、异步任务（进程内执行器）、
inspection-record / photo-report / interview-record 三组业务记录、docxtpl 文书渲染、
Statistics、关键操作审计。
Milestone 3/4：知识库 RAG（解析/分块/embedding/向量库/检索）与三条真实 AI 生成管线。
Milestone 5：任务系统强化（显式状态机、幂等提交、租约与 reaper、死信、通知、并发配置）。
Milestone 6：企业管理 —— 组织/部门/权限矩阵（permissions + role_permissions，幂等种子）、
`/api/admin/*` 管理端点、审计日志查询、`me` 返回生效权限码、统计与业务记录的组织范围。
契约以根目录 `docs/API.md` 为准，表结构以 `docs/DATABASE.md` 为准，编码规则以 `AGENTS.md` 为准。

## 环境搭建

```bash
cd backend
uv venv .venv
uv pip install --python .venv/bin/python \
  fastapi "uvicorn[standard]" pydantic pydantic-settings "sqlalchemy>=2" alembic \
  pyjwt "pwdlib[argon2,bcrypt]" python-multipart email-validator pytest httpx \
  python-docx docxtpl
cp .env.example .env   # 按需修改
```

## 数据库迁移

schema 一律由 Alembic 管理，应用启动时**不会**自动建表，必须先执行迁移：

```bash
.venv/bin/python -m alembic upgrade head
```

新增 schema 变更时（修改 `app/models/` 后）：

```bash
.venv/bin/python -m alembic revision --autogenerate -m "<描述>"
# 检查生成的 alembic/versions/<新文件> 后再 upgrade
```

## 启动

```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

- `GET /health` — 存活探针（公开）
- `POST /api/auth/register` / `POST /api/auth/login` — 公开
- `GET /api/auth/me` / `POST /api/auth/refresh` — 需 `Authorization: Bearer <access_token>`
- `POST /api/inspection-record/generate`、`GET/PUT /api/inspection-record[/...]`、`GET .../download`（API.md §4.1）
- `/api/photo-report`、`/api/interview-record` 同上模式（§4.2 / §4.3）
- `GET /api/tasks`、`GET /api/tasks/{id}`、`POST /api/tasks/{id}/retry|cancel`（§8）
- `GET /api/notifications`、`POST /api/notifications/{id}/read`、`POST /api/notifications/read-all`（§10）
- `GET /api/statistics`（§7）
- `GET/POST /api/admin/organizations`、`PUT/DELETE /api/admin/organizations/{id}`（§11.1）
- `GET/POST /api/admin/departments`、`PUT/DELETE /api/admin/departments/{id}`（§11.2）
- `GET /api/admin/users`、`PUT /api/admin/users/{id}`（§11.3）
- `GET /api/admin/permissions`、`PUT /api/admin/permissions/{role}`（§11.4）
- `GET /api/admin/audit-logs`（§11.5）
- 文档：`http://localhost:8000/docs`

## M6 设计决策（企业管理）

- **权限模型**：权限码目录与默认矩阵在 `app/services/permission_service.py`
  （`PERMISSION_CATALOG` / 默认矩阵），应用启动时幂等种子：permissions 目录缺码补齐，
  role_permissions 仅在空表时填默认矩阵——管理员调整过的矩阵不会被重启覆盖。
  授权依赖 `require_permission("code")`（`app/api/dependencies.py`）按当前用户角色
  查 role_permissions 生效矩阵；`require_roles` 保留兼容。
- **端点切换**：generate（record.create）、记录更新/定稿（service 层：本人记录需
  record.create、他人记录需 record.review、推进 finalized 需 record.finalize）、
  knowledge 上传/删除/重建（knowledge.manage）、tasks retry/cancel（task.manage）、
  statistics（statistics.read）、`/api/admin/*`（admin.orgs / admin.users /
  admin.permissions / admin.audit）。语义只收紧不放松：viewer 不再能创建/修改记录，
  inspector 不再能定稿（specs/_common.md）。
- **管理端点保护**：组织/部门删除在有用户归属时 409；用户部门必须属于其组织（400）；
  禁止把自己停用或降权（409 SELF_LOCKOUT_FORBIDDEN）；admin 角色的 admin.* 权限
  不可移除（409 ADMIN_PERMISSION_LOCKED）。所有管理性变更写 audit_logs
  （`admin.organization.*` / `admin.department.*` / `admin.user.update` /
  `admin.permission.update`）。
- **数据归属**：`records_base._visible_creator_ids` 统一计算可见创建者集合——
  admin=全部；supervisor=所属组织成员（未分配组织回退为仅本人记录）；
  inspector/viewer=本人。三个记录 repository 的 `get_scoped`/`list_scoped` 参数由
  `(user_id, is_admin)` 改为 `creator_ids: list | None`（None=不过滤）。
- **统计 scope**：admin=system；supervisor=organization（按记录创建者所属组织过滤，
  未分配组织的 supervisor 查看全部，scope=system）；inspector/viewer=personal。
  knowledge 计数仍为全库共享。

## M5 设计决策（任务系统强化）

- **显式状态机**：`app/services/tasks/state_machine.py` 的 `TRANSITIONS` 是全平台唯一
  转移表；worker、retry、cancel、管线回写、reaper 的所有状态变更必须经
  `transition()` 校验，非法转移抛 409 `TASK_STATE_CONFLICT`。终态无出边——
  retry 语义为创建新任务实例（`attempt_count` 递增，原任务 id 记入
  `input_data.retry_of`），原任务保留审计。`processing → pending` 仅 reaper 可用。
- **幂等提交**（API.md §1.5）：三个 generate 端点与知识库上传/重建支持
  `Idempotency-Key` 头。存储在 `ai_tasks`：`(created_by, task_type, idempotency_key)`
  唯一索引 + `request_hash`（请求体摘要）。同 key 同体返回首个任务（不重复创建
  上传/草稿/任务），同 key 不同体返回 409 `IDEMPOTENCY_CONFLICT`。
- **执行追踪与租约**：任务创建时写 `queued_at`；worker 认领时写 `worker_id`
  （主机-进程-线程）与 `lease_expires_at`（`TASK_LEASE_SECONDS`），阶段推进时续约。
- **重试上限与死信**：`attempt_count` 达到 `max_attempts`（默认 `TASK_MAX_ATTEMPTS=3`）
  后再次失败即死信等价流程：`failed` + `error_code=RETRY_EXHAUSTED` + 可读中文
  `error_message`（保留原始错误码），并追加 `task.dead_letter` 审计（admin 可追踪）。
- **卡住任务恢复（reaper）**：`app/services/tasks/reaper.py`，挂 lifespan——启动时
  先扫一次（覆盖进程崩溃残留），此后按 `TASK_REAPER_INTERVAL_SECONDS` 周期扫描。
  租约过期且仍在 processing 的任务：attempts 未达上限则重置为 pending 并重新入队
  （`error_code=STALE_TASK_RECOVERED` 标记供排查）；达上限则落 failed 终态
  （`STALE_TASK_RECOVERED`）+ 死信审计 + 通知。重复定稿防护：重新入队的任务仍走
  finalized 防覆盖守卫（worker `_apply_result` 与 TaskService retry 守卫），
  管线落库路径幂等，worker 重启不会静默重复定稿。
- **通知**（API.md §10）：任务进入终态时给创建者写 `notifications`（type
  task_completed/task_failed/task_cancelled，可读中文标题/正文，entity 指向关联
  业务记录或知识文档，兜底指向任务本身）。通知为状态派生物，非事实来源；
  只读本人通知，他人通知一律 404。
- **并发**：执行器并发 worker 数由 `EXECUTOR_WORKERS`（默认 2）配置，进程内
  线程池；多任务并发执行互不干扰（独立 DB 会话、独立取消标记）。
- **可观测性**：结构化日志覆盖 specs/workflow.md §12 信号——认领时记 queue wait
  （`queued_at→started_at`）、attempt/max、worker identity；阶段推进记 stage
  duration；终态记任务总时长、failure code、task_type 与终态。日志带
  task_id/request_id，不含敏感内容。管理性操作记审计：`task.retry` / `task.cancel`
  / `task.dead_letter`。
- **任务响应契约不变**：`attempt_count`/`worker_id`/`lease_expires_at` 等为内部
  运维字段，不暴露于 §8 任务响应（见 API.md §8.1）。

## M2 设计决策

- **download 按需渲染**：`GET .../download` 每次以已保存结构化数据即时渲染 DOCX，
  产生新的 `generated_documents` 版本（version 递增，历史版本文件与元数据均保留、
  不覆盖），保证文书与已保存审阅版本一致。契约中"文档尚未生成返回 409"在此实现中
  仅当渲染不满足业务规则时发生（如拍照报告无选中图片 → 409 `DOCUMENT_NOT_READY`）。
- **finalized 防覆盖**：已 `finalized` 的记录拒绝一切 PUT（含改回其他状态），返回
  409 `RECORD_FINALIZED`；任务重试遇已定稿关联记录返回 409 `TASK_STATE_CONFLICT`。
- **异步任务执行器**：开发态进程内线程池（`app/services/tasks/executor.py`，挂在
  FastAPI lifespan），`TaskExecutor` 抽象为切换 Redis 队列预留（同抽象替换即可）。
  worker 在独立 DB 会话中执行，进度单调不减，取消为尽力而为（阶段边界检查取消标记）。
- **AI 管线骨架**：`app/services/pipelines/` 定义三条生成管线的能力依赖与阶段序列
  （阶段名写入 `ai_tasks.current_stage`）。M2 不接入真实 provider：能力未配置时任务
  failed 且错误可读（`AI_SERVICE_NOT_CONFIGURED`），即使配置了密钥也以
  `AI_PROVIDER_NOT_IMPLEMENTED` 失败 —— 禁止假 AI。M4 实现者见该包 docstring。
- **Word 模板**：`backend/data/templates/*.docx`（docxtpl/Jinja2 占位），由
  `scripts/generate_templates.py` 一次性生成；注意 docxtpl 0.20 的 `{%tr %}` 标签
  在同一表格行内会被贪婪匹配吞掉，for/endfor 必须各占一个独占行（见脚本注释）。
- **Statistics knowledge**：M2 返回全 0 结构；M3 落地 `knowledge_documents` 表后在
  `app/services/statistics_service.py` 接入真实计数。

## 测试

```bash
.venv/bin/python -m pytest
```

测试使用临时 SQLite 库（conftest 中通过 Alembic 迁移建表）与临时存储目录，
任务在真实进程内执行器中跑完（AI 未配置时按预期 failed），无任何外部依赖。

## 设计决策

- **同步 SQLAlchemy 2.x**：M1 无高并发长 IO 需求，同步 session 语义简单且与 Alembic 天然一致；路由用普通 `def`（FastAPI 在线程池执行），不阻塞事件循环。后续若引入异步任务队列再评估切换。
- **数据库兼容**：默认 SQLite 便于本地开发；JSON 列使用 `sqlalchemy.JSON().with_variant(JSONB, "postgresql")`（见 `app/models/base.py` 的 `JSONVariant`），时间戳统一 `DateTime(timezone=True)` + UTC，切换 PostgreSQL 只需改 `DATABASE_URL`。
- **分层**：router 保持薄；业务规则在 `app/services/`（如 `AuthService`）；DB 访问在 `app/repositories/`。
- **错误信封**：所有错误响应为 `{"error": {"code", "message"}}`，由 `app/core/exceptions.py` 的全局 handler 统一产出；业务代码抛 `AppException`。
- **防账号枚举**：登录失败（邮箱不存在/密码错误/账号停用）统一返回 `401 UNAUTHORIZED` 与相同提示。

## 后续 milestone 约定

- **加 router**：在 `app/api/routers/` 新建文件，`main.py` 中 `app.include_router(x.router, prefix="/api")`。
- **加 model**：`app/models/` 下新建模块并继承 `app.models.base.Base`；在 `alembic/env.py` 中 import 该模块后 autogenerate migration。
- **取当前用户**：路由参数声明 `current_user: CurrentUser`（`app/api/dependencies.py`）；角色限制用 `Depends(require_roles("admin", ...))`。
- **取配置**：业务代码一律 `from app.core.config import get_settings`，禁止散落读取环境变量。
- **DB 会话**：路由参数声明 `session: DbSession`（`get_db` 依赖）。
- **审计**：`AuditLogRepository.append(...)` 只追加；不记录密码/token/敏感文档内容。
- **存储**：业务代码只依赖 `app.services.storage.StorageService` 抽象，通过 `get_storage_service()` 获取实现。
