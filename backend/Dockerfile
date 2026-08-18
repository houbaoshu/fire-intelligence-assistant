# Fire Intelligence Platform 后端镜像（M7）
# 视频/音频处理所需的 ffmpeg 二进制由 imageio-ffmpeg 的 wheel 自带，slim 镜像可用。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 应用代码、迁移、Word 模板与运维脚本（setuptools 打包需要 app/ 在场，先拷贝再安装）
COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY data/templates ./data/templates
COPY scripts ./scripts

# 安装依赖（含 postgres 驱动，便于 compose 直接切换 PostgreSQL；S3 按需另装 .[s3]）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[postgres]"

# 非 root 运行；/app/data 为 SQLite/存储/向量库默认数据目录（建议挂卷）
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 启动时应用自动执行 alembic upgrade head 与默认管理员种子（见 app/main.py lifespan）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
