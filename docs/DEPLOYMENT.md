# DEPLOYMENT.md

# 部署指南（平台工程化 · Milestone 7）

本文件说明目标生产部署方式。配置一律来自环境变量，严禁硬编码密钥。环境变量命名以 docs/PROJECT.md 为准。

## 快速启动（Docker Compose）

1. 复制环境变量模板并填写密钥：

```bash
cp backend/.env.example backend/.env
# 生产环境必须设置强随机 JWT_SECRET
```

2. 启动：

```bash
docker compose up -d --build
```

3. 验证：

```bash
curl http://localhost:8000/health    # {"status":"ok"}
curl http://localhost:8000/metrics   # Prometheus 指标
```

服务启动时自动执行数据库 migration（`AUTO_MIGRATE=true`），并幂等创建默认管理员（环境变量 `DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD`）。

## 本地开发

后端（Node.js + TypeScript）：

```bash
cd backend
npm install
cp .env.example .env        # 按需修改 DATABASE_URL 等
npm run migrate             # 执行 migration（具体命令由所选 ORM 决定）
npm run dev                 # 启动开发服务器（监听 :8000）
```

前端（框架由实现时按 docs/ARCHITECTURE.md §4.1 选定）：

```bash
cd frontend
npm install
# API Base URL 通过构建时环境变量注入（变量名以所选框架惯例为准）
npm run dev
```

## AI 服务配置

后端通过 OpenAI 兼容 API 调用所有 AI 能力，模型名称一律来自环境变量：

| 环境变量 | 用途 |
| --- | --- |
| `AI_LLM_API_KEY` / `AI_LLM_MODEL` / `AI_LLM_BASE_URL` | 大语言模型 |
| `AI_VISION_API_KEY` / `AI_VISION_MODEL` / `AI_VISION_BASE_URL` | 视觉模型 |
| `AI_OCR_API_KEY` / `AI_OCR_MODEL` / `AI_OCR_BASE_URL` | OCR |
| `AI_SPEECH_API_KEY` / `AI_SPEECH_MODEL` / `AI_SPEECH_BASE_URL` | 语音识别 |
| `AI_EMBEDDING_API_KEY` / `AI_EMBEDDING_MODEL` / `AI_EMBEDDING_BASE_URL` | Embedding |
| `AI_RERANKER_API_KEY` / `AI_RERANKER_MODEL` / `AI_RERANKER_BASE_URL` | 可选 reranker（未配置则跳过 rerank） |

未配置 AI 时，系统仍可正常使用认证、记录管理、知识库上传等非 AI 功能；AI 相关操作必须返回可读的 `AI_NOT_CONFIGURED` 错误，不得编造结果。

## 数据库

- 生产使用 PostgreSQL：`DATABASE_URL=postgresql://user:pass@host:5432/fire_intelligence`。
- 开发可使用 PostgreSQL 本地实例或 Docker 容器。
- schema 变更一律通过 migration（工具由所选 ORM 决定），禁止手工改表。

## 存储

- `STORAGE_PROVIDER=local`（默认，开发 / 单实例自托管，文件落在 `STORAGE_DIR`；多实例部署不适用）。
- `STORAGE_PROVIDER=s3`（需 `S3_*` 变量）或 `supabase`（需 `SUPABASE_*` 变量）。

## 监控

- `GET /metrics` 暴露 Prometheus 文本格式指标（请求计数、耗时直方图）。
- 可配合 Prometheus + Grafana 采集；指标实现无外部依赖，可替换为完整可观测栈。

## 备份

- PostgreSQL：使用 `pg_dump`。
- 对象存储与向量库：按所选 provider 的快照 / 归档方案执行。

## CI/CD

每次推送运行：后端测试 + typecheck/lint/build，前端 typecheck/lint/build。构建失败必须阻断合并。

## 缓存与性能

- 统计类只读接口（如知识库状态）使用进程内 TTL 缓存，可替换为 Redis。
- 长耗时 AI 操作一律走异步任务（`ai_tasks` + worker），不阻塞 HTTP 请求。
- 大文件上传有严格的类型/大小/签名校验；临时处理文件自动清理。
