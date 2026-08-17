"""Statistics 路由（API.md §7）。"""

from fastapi import APIRouter, Depends

from app.api.dependencies import DbSession, require_permission
from app.models.user import User
from app.schemas.statistics import StatisticsResponse
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsResponse)
def get_statistics(
    session: DbSession,
    current_user: User = Depends(require_permission("statistics.read")),
) -> StatisticsResponse:
    return StatisticsService(session).get(current_user)
