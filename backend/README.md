# Fire Intelligence Platform — Backend

FastAPI 后端。Milestone 1：认证（注册/登录/me/refresh）、健康检查、存储抽象骨架。
Milestone 2：消防检查工作流 —— 文件上传四重校验、异步任务（进程内执行器）、
inspection-record / photo-report / interview-record 三组业务记录、docxtpl 文书渲染、
Statistics、关键操作审计。
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
- `GET /api/statistics`（§7）
- 文档：`http://localhost:8000/docs`

## M2 设计决策

- **download 按需渲染**：`GET .../download` 每次以已保存结构化数据即时渲染 DOCX，
  产生新的 `generated_documents` 版本（version 递增，历史版本文件与元数据均保留、
  不覆盖），保证文书与已保存审阅版本一致。契约中"文档尚未生成返回 409"在此实现中
  仅当渲染不满足业务规则时发生（如拍照报告无选中图片 → 409 `DOCUMENT_NOT_READY`）。
- **finalized 防覆盖**：已 `finalized` 的记录拒绝一切 PUT（含改回其他状态），返回
  409 `RECORD_FINALIZED`；任务重试遇已定稿关联记录返回 409 `TASK_STATE_CONFLICT`。
- **异步任务执行器**：开发态进程内线程池（`app/services/tasks/executor.py`，挂在
  FastAPI lifespan），`TaskExecutor` 抽象为 M5 切换 Redis 队列预留。worker 在独立
  DB 会话中执行，进度单调不减，取消为尽力而为（阶段边界检查取消标记）。
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
