# ==============================================================================
# Stage 1: Build frontend (TanStack Start + Nitro)
# ==============================================================================
FROM oven/bun:1 AS frontend-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY frontend/ .
RUN bun run build

# ==============================================================================
# Stage 2: Production image — Python backend + Node frontend
# ==============================================================================
FROM python:3.11-slim AS backend

# Node.js is needed to run the Nitro-rendered TanStack Start frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Copy backend code
COPY backend/ .

# Copy built frontend (Nitro output includes a Node.js server)
COPY --from=frontend-build /app/frontend/.output ./frontend/.output

# Create data directories
RUN mkdir -p data/storage data/templates data/temporary

EXPOSE 8000

# Start the FastAPI backend.
# The TanStack Start frontend can be started separately via:
#   node /app/frontend/.output/server/index.mjs
# or by adding a reverse proxy (nginx) in front of both services.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
