# DEPLOYMENT.md

# 部署指南(平台工程化 · Milestone 7)

本文件说明生产部署方式。配置一律来自环境变量,严禁硬编码密钥。

## 快速启动(Docker Compose)

1. 复制环境变量模板并填写密钥:

```bash
cp backend/.env.example .env
export SECRET_KEY="$(openssl rand -hex 32)"  # 必填,生产环境必须设置
```

2. 启动:

```bash
docker compose up -d --build
```

3. 验证:

```bash
curl http://localhost:8000/health   # {"status":"ok"}
curl http://localhost:8000/api/docs  # OpenAPI 文档
curl http://localhost:8000/metrics   # Prometheus 指标
```

服务启动时自动执行 Alembic migration,并幂等创建默认管理员(环境变量 `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD`)。

## 本地开发

```bash
cd backend
uv venv --python 3.11 .venv && source .venv/bin/activate
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

后端通过 OpenAI 兼容 API 调用所有 AI 能力,模型名称一律来自环境变量:

| 环境变量 | 用途 |
| --- | --- |
| `OPENAI_API_KEY` | 服务密钥(必填才能启用 AI) |
| `AI_BASE_URL` | OpenAI 兼容 Base URL(DeepSeek / Qwen / 本地 vLLM 等) |
| `LLM_MODEL` / `VISION_MODEL` / `OCR_MODEL` / `SPEECH_MODEL` / `EMBEDDING_MODEL` | 各能力模型名 |
| `RERANK_MODEL` / `RERANK_BASE_URL` | 可选 reranker(未配置则跳过 rerank) |

未配置 AI 时,系统仍可正常使用认证、记录管理、知识库上传等非 AI 功能;AI 相关操作会返回可读的 `AI_NOT_CONFIGURED` 错误,不会编造结果。

## 数据库

- 默认 SQLite(`sqlite:///./data/app.db`),适合开发与单机部署。
- 生产建议 PostgreSQL:`DATABASE_URL=postgresql+psycopg://user:pass@host:5432/fire_intelligence`。
- schema 变更一律通过 Alembic migration(`alembic revision --autogenerate` + `alembic upgrade head`)。

## 存储

- `STORAGE_PROVIDER=local`(默认,开发/自托管)。
- `STORAGE_PROVIDER=s3`(需 `S3_*` 变量)或 `supabase`(需 `SUPABASE_*` 变量)。

## 监控

- `GET /metrics` 暴露 Prometheus 文本格式指标(请求计数、耗时直方图)。
- 可配合 Prometheus + Grafana 采集;指标实现无外部依赖,可替换为完整可观测栈。

## 备份

```bash
cd backend && ./scripts/backup.sh ../backups
```

输出:SQLite 数据库快照、对象存储归档、向量库快照(如使用 local 向量库)。PostgreSQL 环境请使用 `pg_dump`。

## CI/CD

`.github/workflows/ci.yml` 在每次推送时运行:后端 pytest 全量测试 + 前端 typecheck/lint/build。

## 缓存与性能

- 统计类只读接口(如知识库状态)使用进程内 TTL 缓存(`app/core/cache.py`),可替换为 Redis。
- 长耗时 AI 操作一律走异步任务(`ai_tasks` + worker),不阻塞 HTTP 请求。
- 大文件上传有严格的类型/大小/签名校验;临时处理文件自动清理。
