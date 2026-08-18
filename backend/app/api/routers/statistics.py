"""Statistics 路由（API.md §7）。

只读聚合结果走进程内 TTL 缓存（M7，`app/core/cache.py`）：按用户维度缓存
（scope 由角色/组织派生），TTL 由 ``CACHE_TTL_SECONDS`` 配置；记录/知识库/
任务终态变更后按前缀失效（见 ``invalidate_read_models``）。
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import DbSession, require_permission
from app.core.cache import PREFIX_STATISTICS, get_cache
from app.core.config import get_settings
from app.models.user import User
from app.schemas.statistics import StatisticsResponse
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsResponse)
def get_statistics(
    session: DbSession,
    current_user: User = Depends(require_permission("statistics.read")),
) -> StatisticsResponse:
    cache_key = f"{PREFIX_STATISTICS}{current_user.id}"
    cached = get_cache().get(cache_key)
    if isinstance(cached, StatisticsResponse):
        return cached
    result = StatisticsService(session).get(current_user)
    get_cache().set(cache_key, result, get_settings().CACHE_TTL_SECONDS)
    return result
