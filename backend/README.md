# Fire Intelligence Backend

FastAPI backend for the Fire Intelligence Platform. It provides authentication,
inspection workflows, protected storage, durable background tasks, configurable
AI/media pipelines, RAG, DOCX generation, statistics, enterprise authorization,
audit records, and AI-platform registries.

## Run locally

```bash
cp .env.example .env
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The development default uses SQLite and protected local storage under `data/`.
Set `APP_DATABASE_URL` to a PostgreSQL SQLAlchemy URL for shared environments.
Production startup requires `APP_AUTH_SECRET_KEY`; development creates a local,
git-ignored signing key when that variable is empty.

AI workflows use an OpenAI-compatible base URL, API key, and separate model names
for language, vision, speech, and embeddings. Missing capabilities fail explicitly;
the regulation QA endpoint can still return retrieved source excerpts without an LLM.
The remaining AI timeouts, retrieval, chunking, frame, upload, and task-recovery
settings are documented in `.env.example`.

See `../DEPLOYMENT.md` for containers, scaling boundaries, backups, and restore guidance.

## Verify

```bash
uv run ruff check .
uv run mypy app
uv run pytest
uv run alembic upgrade head
```
