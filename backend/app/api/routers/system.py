from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user
from app.core.permissions import require_admin
from app.db.models import User

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/capabilities")
def capabilities(request: Request, _: User = Depends(get_current_user)) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "application_version": settings.version,
        "environment": settings.environment,
        "features": {
            "llm": bool(settings.ai_base_url and settings.ai_api_key and settings.llm_model),
            "vision": bool(settings.ai_base_url and settings.ai_api_key and settings.vision_model),
            "speech": bool(settings.ai_base_url and settings.ai_api_key and settings.speech_model),
            "embedding": bool(
                settings.ai_base_url and settings.ai_api_key and settings.embedding_model
            ),
            "local_storage": settings.storage_backend == "local",
            "durable_tasks": True,
        },
        "limits": {
            "video_bytes": settings.max_video_bytes,
            "audio_bytes": settings.max_audio_bytes,
            "document_bytes": settings.max_document_bytes,
        },
    }


@router.get("/metrics")
def metrics(request: Request, _: User = Depends(require_admin)) -> dict[str, int | float]:
    values = request.app.state.request_metrics
    requests = int(values["requests"])
    return {
        "requests_total": requests,
        "errors_total": int(values["errors"]),
        "average_duration_ms": round(float(values["duration_ms"]) / max(1, requests), 2),
    }
