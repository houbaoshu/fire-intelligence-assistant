"""SQLAlchemy Declarative Base 与公共类型。"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# 兼容 PostgreSQL 的 JSON 类型：SQLite 用 JSON，PostgreSQL 用 JSONB
JSONVariant = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


UTCDateTime = DateTime(timezone=True)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
