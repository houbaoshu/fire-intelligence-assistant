"""Regulation QA schema（API.md §5）。"""

import uuid
from datetime import date

from pydantic import BaseModel, field_validator

QUESTION_MAX_LENGTH = 4000  # specs/regulation-qa.md：问题长度上限


class QAQueryRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def _validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("问题不能为空")
        if len(question) > QUESTION_MAX_LENGTH:
            raise ValueError(f"问题长度超过上限（{QUESTION_MAX_LENGTH} 字符）")
        return question


class QASource(BaseModel):
    """来源元素字段严格对齐 API.md §5 契约。"""

    document_id: uuid.UUID
    title: str | None
    article: str | None
    page: int | None
    excerpt: str
    effective_date: date | None


class QAQueryResponse(BaseModel):
    answer: str
    sources: list[QASource]
