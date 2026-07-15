"""Fire regulation Q&A endpoint with RAG retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.qa import QAQueryRequest, QAResponse

logger = get_logger(__name__)

router = APIRouter(tags=["qa"])


@router.post(
    "/query",
    response_model=QAResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a fire regulation question",
)
async def query(
    body: QAQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAResponse:
    """Answer a fire-regulation question using RAG retrieval.

    The question is embedded, relevant document chunks are retrieved from
    the knowledge base, reranked, and passed to the LLM together with the
    original question to produce a grounded answer with source citations.
    """
    from app.services.qa_service import QAService

    logger.info(
        "QA query from user %s: %s",
        current_user.id,
        body.question[:80],
    )

    service = QAService(db=db)
    result = await service.answer(body.question)
    return result
