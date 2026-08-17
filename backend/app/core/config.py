"""应用配置：全部来自环境变量（见 backend/.env.example），禁止硬编码密钥。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 数据库：默认本地 SQLite 便于开发；生产使用 PostgreSQL，
    # 例如 postgresql+psycopg2://user:pass@host:5432/fire
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS（逗号分隔）
    CORS_ORIGINS: str = "http://localhost:3000"

    # 注册开关
    REGISTRATION_ENABLED: bool = True

    # 存储
    STORAGE_PROVIDER: str = "local"
    STORAGE_DIR: str = "./data/storage"

    # 业务规则
    REMARKS_MAX_LENGTH: int = 2000

    # AI 能力配置（为空表示未配置；未配置时相关任务/请求以可读错误失败，
    # 不会编造结果。全部走 OpenAI 兼容 HTTP API，base_url 必须显式配置）
    AI_LLM_API_KEY: str = ""
    AI_LLM_MODEL: str = ""
    AI_LLM_BASE_URL: str = ""
    AI_VISION_API_KEY: str = ""
    AI_VISION_MODEL: str = ""
    AI_VISION_BASE_URL: str = ""
    AI_OCR_API_KEY: str = ""
    AI_OCR_MODEL: str = ""
    AI_OCR_BASE_URL: str = ""
    AI_SPEECH_API_KEY: str = ""
    AI_SPEECH_MODEL: str = ""
    AI_SPEECH_BASE_URL: str = ""
    AI_EMBEDDING_API_KEY: str = ""
    AI_EMBEDDING_MODEL: str = ""
    AI_EMBEDDING_BASE_URL: str = ""
    AI_RERANKER_API_KEY: str = ""
    AI_RERANKER_MODEL: str = ""
    AI_RERANKER_BASE_URL: str = ""
    # AI HTTP 调用：超时与有限重试
    AI_HTTP_TIMEOUT_SECONDS: float = 60.0
    AI_HTTP_MAX_RETRIES: int = 2

    # 视频/音频媒体处理（M4 管线：抽帧间隔、关键帧上限、临时工作区目录）
    MEDIA_FRAME_INTERVAL_SECONDS: float = 2.0
    MEDIA_MAX_KEY_FRAMES: int = 12
    # 抽帧/抽音频中间产物的临时目录（用后清理，见 specs/_common.md）
    MEDIA_TEMP_DIR: str = "./data/temporary"

    # 向量库（local=内置本地实现，存 VECTOR_STORE_DIR；chroma=可选 provider，需安装 chromadb）
    VECTOR_STORE_PROVIDER: str = "local"
    VECTOR_STORE_DIR: str = "./data/vectorstore"

    # RAG 检索参数（specs/regulation-qa.md：默认参数来自后端配置）
    RAG_RETRIEVAL_TOP_K: int = 8
    RAG_CONTEXT_TOP_N: int = 5

    # 异步任务执行器（in_process 为开发态进程内线程池；可替换为 Redis 队列实现同一抽象）
    TASK_EXECUTOR: str = "in_process"
    # 执行器并发 worker 数（进程内线程池大小）
    EXECUTOR_WORKERS: int = 2
    # 任务重试上限：attempt_count 达到 max_attempts 后失败即死信（RETRY_EXHAUSTED）
    TASK_MAX_ATTEMPTS: int = 3
    # worker 租约时长（秒）：阶段推进时续约；过期未续约视为卡住，由 reaper 恢复
    TASK_LEASE_SECONDS: float = 300.0
    # reaper 周期扫描间隔（秒）；应用启动时也会立即执行一次恢复
    TASK_REAPER_INTERVAL_SECONDS: float = 60.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
