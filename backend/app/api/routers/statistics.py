"""Statistics 路由（API.md §7）。"""

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.statistics import StatisticsResponse
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsResponse)
def get_statistics(session: DbSession, current_user: CurrentUser) -> StatisticsResponse:
    return StatisticsService(session).get(current_user)
