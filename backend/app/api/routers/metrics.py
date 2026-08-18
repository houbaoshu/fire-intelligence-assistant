"""Prometheus 指标端点（M7，公开，不在 /api 前缀之下；自身不计入请求指标）。"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.metrics import get_metrics_registry

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        get_metrics_registry().render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
