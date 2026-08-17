"""共享 schema 基础设施：UTC 时间归一化与分页信封（API.md §1.2 / §4）。"""

from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, field_validator

ItemT = TypeVar("ItemT", bound=BaseModel)


class UTCModel(BaseModel):
    """SQLite 驱动返回 naive datetime，统一按 UTC 归一化为 aware 后序列化。"""

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def _normalize_datetime(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Page(UTCModel, Generic[ItemT]):
    items: list[ItemT]
    total: int
    page: int
    page_size: int
