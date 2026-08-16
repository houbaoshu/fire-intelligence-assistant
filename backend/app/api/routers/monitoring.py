"""Monitoring endpoints: health probe and Prometheus metrics."""
from __future__ import annotations

from fastapi import APIRouter, Response

from app.core import metrics

router = APIRouter(tags=["monitoring"])

metrics.describe("http_requests", "Total HTTP requests")
metrics.describe("http_request_duration_seconds", "HTTP request duration")


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Prometheus text exposition format."""
    return Response(
        content=metrics.render_metrics(),
        media_type="text/plain; version=0.0.4",
    )
