"""法规问答业务逻辑（API.md §5）。薄封装：查询管线实现见 app/rag/query.py。"""

from sqlalchemy.orm import Session

from app.rag.query import QAResult, run_query


class QAService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def answer(self, question: str) -> QAResult:
        return run_query(self.session, question)
