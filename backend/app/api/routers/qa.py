"""Regulation QA endpoint (API.md §5)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DB
from app.schemas.qa import QAQueryRequest, QAQueryResponse
from app.services.qa_service import QAService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/query", response_model=QAQueryResponse)
def query(user: CurrentUser, db: DB, payload: QAQueryRequest):
    result = QAService(db).query(user, payload.question)
    return QAQueryResponse(**result)
