"""Statistics endpoint (API.md §7)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DB
from app.schemas.statistics import StatisticsResponse
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsResponse)
def statistics(user: CurrentUser, db: DB):
    data = StatisticsService(db).get(user)
    return StatisticsResponse(**data)
