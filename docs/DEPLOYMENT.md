# DEPLOYMENT.md

# 部署指南(平台工程化 · Milestone 7)

本文件说明生产部署方式。配置一律来自环境变量,严禁硬编码密钥。全部可用变量见 `backend/.env.example`。

## 快速启动(Docker Compose)

1. 复制环境变量模板并填写密钥:

```bash
cp backend/.env.example .env
# 必填:生产环境必须设置强随机 JWT_SECRET
sed -i '' "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 32)/" .env
# 可选:默认管理员(启动时幂等创建,邮箱已存在则跳过)
# DEFAULT_ADMIN_EMAIL=admin@example.com
# DEFAULT_ADMIN_PASSWORD=<强密码>
```

2. 启动:

```bash
docker compose up -d --build
```

3. 验证:

```bash
curl http://localhost:8000/health   # {"status":"ok"}
curl http://localhost:8000/docs     # OpenAPI 文档
curl http://localhost:8000/metrics  # Prometheus 指标
```

服务启动时自动执行 Alembic migration(`AUTO_MIGRATE=true`,默认开;关闭后需自行
`alembic upgrade head`),并幂等创建默认管理员(环境变量 `DEFAULT_ADMIN_EMAIL` /
`DEFAULT_ADMIN_PASSWORD`,仅当两者都设置且邮箱不存在时创建 role=admin;密码不落日志)。

默认单容器 + SQLite 即可跑通(数据在 `backend-data` 卷)。生产 PostgreSQL:在 `.env`
中设置 `DATABASE_URL=postgresql+psycopg://fire:fire@postgres:5432/fire`,compose 中的
`postgres` 服务即指向它(镜像已安装 `postgres` extra 驱动)。

## 本地开发

```bash
cd backend
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env   # 按需修改 DATABASE_URL 等
alembic upgrade head
uvicorn app.main:app --reload
```

前端:

```bash
cd frontend
bun install
VITE_API_BASE_URL=http://localhost:8000 bun run dev
```

## AI 服务配置

后端通过 OpenAI 兼容 API 调用所有 AI 能力,每种能力独立配置三元组
(`AI_<CAP>_API_KEY` / `AI_<CAP>_MODEL` / `AI_<CAP>_BASE_URL`,Base URL 必须显式配置):

| 能力 | 环境变量前缀 |
| --- | --- |
| 大语言模型 | `AI_LLM_*` |
| 视觉模型 | `AI_VISION_*` |
| OCR | `AI_OCR_*` |
| 语音转写 | `AI_SPEECH_*` |
| Embedding | `AI_EMBEDDING_*` |
| Reranker(可选,未配置则跳过 rerank) | `AI_RERANKER_*` |

未配置 AI 时,系统仍可正常使用认证、记录管理、知识库上传等非 AI 功能;AI 相关操作会返回可读的 `AI_SERVICE_NOT_CONFIGURED` 错误,不会编造结果。

## 数据库

- 默认 SQLite(`sqlite:///./data/app.db`),适合开发与单机部署。
- 生产建议 PostgreSQL:`DATABASE_URL=postgresql+psycopg://user:pass@host:5432/fire_intelligence`
  (驱动为 optional 依赖:`pip install '.[postgres]'`;Docker 镜像已内置)。
- PostgreSQL 连接池可配:`DB_POOL_SIZE`(默认 5)/ `DB_MAX_OVERFLOW`(默认 10)。
- schema 变更一律通过 Alembic migration(`alembic revision --autogenerate` + `alembic upgrade head`)。

## 存储

- `STORAGE_PROVIDER=local`(默认,开发/自托管),文件落 `STORAGE_DIR`。
- `STORAGE_PROVIDER=s3`:S3 兼容对象存储,需安装 `pip install '.[s3]'`(boto3),变量:
  `S3_BUCKET`(必填)/ `S3_REGION` / `S3_ENDPOINT_URL` / `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`。
- `STORAGE_PROVIDER=supabase`:Supabase Storage 走 S3 兼容端点,复用同一组 `S3_*` 变量,
  将 `S3_ENDPOINT_URL` 指向 Supabase 项目的 S3 endpoint
  (`https://<project-ref>.supabase.co/storage/v1/s3`),凭证用 Supabase S3 access key。

## 监控

`GET /metrics` 暴露 Prometheus 文本格式指标(无外部依赖自实现,`app/core/metrics.py`):

| 指标 | 类型 | 标签 | 说明 |
| --- | --- | --- | --- |
| `http_requests_total` | counter | `method` `route` `status` | 请求计数;`route` 为路由模板(如 `/api/tasks/{task_id}`)避免高基数,未匹配记为 `unmatched`;`/metrics` 自身不计入 |
| `http_request_duration_seconds` | histogram | `method` `route` | 请求耗时 |
| `ai_tasks_terminal_total` | counter | `task_type` `status` | 任务终态计数;进程内累计,**进程重启清零** |

可配合 Prometheus + Grafana 采集;指标注册表接口简单,可替换为完整可观测栈。
结构化日志(ARCHITECTURE.md §18.5)继续覆盖任务/请求级信号。

## 备份

```bash
cd backend && ./scripts/backup.sh ../backups
```

输出带时间戳的目录 `backup-YYYYmmdd-HHMMSS`,包含:

- SQLite:`db.sqlite3` 在线快照(`sqlite3 .backup`;无 sqlite3 时退化为文件拷贝并警告)。
- PostgreSQL:DATABASE_URL 为 PG 时自动使用 `pg_dump`(自定义格式 `db.dump`);
  未安装 pg_dump 时可读报错并非零退出。
- `storage.tar.gz`:本地对象存储目录归档。
- `vectorstore.tar.gz`:本地向量库快照(`VECTOR_STORE_PROVIDER=local` 时)。

恢复步骤:

```bash
# SQLite:停服后用快照替换数据库文件,再启动(启动自动迁移到 head)
cp backups/backup-<ts>/db.sqlite3 backend/data/app.db
# PostgreSQL:
pg_restore --clean --if-exists -d "$DATABASE_URL" backups/backup-<ts>/db.dump
# 存储与向量库:解包回对应目录
tar -xzf backups/backup-<ts>/storage.tar.gz -C backend/data/storage
tar -xzf backups/backup-<ts>/vectorstore.tar.gz -C backend/data/vectorstore
```

## CI/CD

`.github/workflows/ci.yml` 在 push/PR 时运行:后端 job(uv 安装依赖 + pytest 全量)、
前端 job(bun install + `bunx tsc --noEmit` + `bun run lint` + `bun run build`)。

## 缓存与性能

- 只读聚合接口 `GET /api/statistics` 与 `GET /api/knowledge/status` 使用进程内 TTL 缓存
  (`app/core/cache.py`,TTL 由 `CACHE_TTL_SECONDS` 配置,默认 30s);记录/知识库变更与任务
  终态后按前缀失效;接口可替换为 Redis(多实例部署时应替换)。
- 长耗时 AI 操作一律走异步任务(`ai_tasks` + worker),不阻塞 HTTP 请求。
- 大文件上传有严格的类型/大小/签名校验;临时处理文件自动清理。
