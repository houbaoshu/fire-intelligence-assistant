"""法规问答路由（API.md §5）。保持薄：同步执行查询管线（不走异步任务）。"""

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.qa import QAQueryRequest, QAQueryResponse
from app.services.qa_service import QAService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/query", response_model=QAQueryResponse)
def query(
    payload: QAQueryRequest, session: DbSession, current_user: CurrentUser
) -> QAQueryResponse:
    result = QAService(session).answer(payload.question)
    return QAQueryResponse(answer=result.answer, sources=result.sources)
