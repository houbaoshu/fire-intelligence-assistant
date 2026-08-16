"""Statistics schemas (API.md §7)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RecordGroupStats(BaseModel):
    total: int
    by_status: dict[str, int]


class StatisticsResponse(BaseModel):
    scope: str
    generated_at: datetime
    records: dict[str, RecordGroupStats]
    tasks: RecordGroupStats
    knowledge: dict[str, Any]
    generated_documents: dict[str, int]
