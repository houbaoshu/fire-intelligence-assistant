from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    with request.app.state.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    request.app.state.storage.initialize()
    return {"status": "ok"}
