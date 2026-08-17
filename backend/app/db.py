"""数据库引擎与会话。

- 同步 SQLAlchemy 2.x（见 README「设计决策」）。
- 兼容 PostgreSQL：JSON 列使用 ``sqlalchemy.JSON`` 并 ``with_variant(JSONB, "postgresql")``；
  时间戳统一 UTC（``DateTime(timezone=True)``）。
- 禁止自动建表（``create_all``），schema 变更必须走 Alembic migration。
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_engine_from_url(database_url: str) -> Engine:
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


engine = create_engine_from_url(get_settings().DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
