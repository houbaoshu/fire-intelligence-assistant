"""评估运行器（M8，API.md §12.3）。

真实调用 RAG+LLM 查询管线（复用 M3 ``app.rag.query.run_query``），按规则
逐题记分：

- ``expected_keywords``：期望关键词命中率（全部命中该题此项才算通过）；
- ``require_source``：回答必须附检索来源（sources 非空）；
- ``expect_refusal``：期望拒答——检索无依据时应诚实拒答（sources 为空）。

逐题超时保护（EVAL_QUESTION_TIMEOUT_SECONDS）：超时/管线异常记为不通过，
错误信息写入 details，不中断整轮评估。
"""

import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException, not_found
from app.core.logging import get_logger
from app.models.ai_platform import EvaluationResult
from app.rag.query import run_query
from app.schemas.ai_platform import EvaluationQuestion

logger = get_logger("evaluation")

_ANSWER_PREVIEW_CHARS = 500


class EvaluationService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self._settings = settings or get_settings()

    def run(
        self,
        name: str,
        questions: list[EvaluationQuestion],
        created_by: uuid.UUID | None,
    ) -> EvaluationResult:
        details = [self._evaluate(q) for q in questions]
        passed = sum(1 for d in details if d["passed"])
        row = EvaluationResult(
            name=name,
            status="completed",
            total_questions=len(questions),
            passed=passed,
            details=details,
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list(self, page: int, page_size: int) -> tuple[list[EvaluationResult], int]:
        total = self.session.execute(
            select(func.count()).select_from(EvaluationResult)
        ).scalar_one()
        stmt = (
            select(EvaluationResult)
            .order_by(EvaluationResult.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.execute(stmt).scalars().all()), total

    def get(self, evaluation_id: uuid.UUID) -> EvaluationResult:
        row = self.session.get(EvaluationResult, evaluation_id)
        if row is None:
            raise not_found("评估结果不存在")
        return row

    # ---------- 逐题执行与计分 ----------

    def _evaluate(self, question: EvaluationQuestion) -> dict:
        detail: dict = {
            "question": question.question,
            "passed": False,
            "checks": [],
            "error": None,
        }
        result, error = self._run_with_timeout(question.question)
        if error is not None:
            detail["error"] = error
            return detail
        assert result is not None
        detail["answer"] = result.answer[:_ANSWER_PREVIEW_CHARS]
        detail["sources_count"] = len(result.sources)

        checks: list[dict] = []
        if question.expected_keywords:
            hits = [k for k in question.expected_keywords if k in result.answer]
            checks.append(
                {
                    "rule": "expected_keywords",
                    "passed": len(hits) == len(question.expected_keywords),
                    "hit_rate": round(len(hits) / len(question.expected_keywords), 4),
                    "missed": [k for k in question.expected_keywords if k not in hits],
                }
            )
        if question.require_source:
            checks.append(
                {"rule": "require_source", "passed": len(result.sources) > 0}
            )
        if question.expect_refusal:
            checks.append(
                {"rule": "expect_refusal", "passed": len(result.sources) == 0}
            )
        if not checks:
            # 未指定规则：管线正常返回非空回答即通过
            checks.append(
                {"rule": "answered", "passed": bool(result.answer.strip())}
            )
        detail["checks"] = checks
        detail["passed"] = all(c["passed"] for c in checks)
        return detail

    def _run_with_timeout(self, question: str):
        """在新会话中同步执行查询管线，超时返回可读错误（不中断整轮）。"""
        from app.db import SessionLocal

        def _call():
            # 独立会话：避免与请求会话跨线程共享
            with SessionLocal() as query_session:
                return run_query(query_session, question)

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_call)
        try:
            return future.result(timeout=self._settings.EVAL_QUESTION_TIMEOUT_SECONDS), None
        except FuturesTimeout:
            return None, f"单题评估超时（>{self._settings.EVAL_QUESTION_TIMEOUT_SECONDS:.0f}s）"
        except AppException as exc:
            return None, f"{exc.code}: {exc.message}"
        except Exception as exc:
            logger.info("评估题目执行异常: %s", type(exc).__name__)
            return None, f"管线执行失败（{type(exc).__name__}）"
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
