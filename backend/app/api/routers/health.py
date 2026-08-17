"""健康检查路由（API.md §3，公开，不在 /api 前缀之下）。"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
