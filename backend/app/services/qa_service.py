"""法规问答业务逻辑（API.md §5）。薄封装：查询管线实现见 app/rag/query.py。

产出回答后触发插件钩子 ``on_qa_answer``（M8）：启用中的插件可就地修改
回答（如 qa_disclaimer 追加免责说明），启用状态以 plugins 表为准。
"""

from sqlalchemy.orm import Session

from app.plugins import run_hook
from app.rag.query import QAResult, run_query


class QAService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def answer(self, question: str) -> QAResult:
        result = run_query(self.session, question)
        context = run_hook(
            self.session,
            "on_qa_answer",
            {"question": question, "answer": result.answer, "sources": result.sources},
        )
        if context.get("answer") != result.answer:
            result.answer = context["answer"]
        return result
