"""interview_records 数据访问。业务规则不得出现在此层。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.interview import InterviewRecord


class InterviewRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_scoped(
        self, record_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool
    ) -> InterviewRecord | None:
        stmt = select(InterviewRecord).where(
            InterviewRecord.id == record_id, InterviewRecord.deleted_at.is_(None)
        )
        if not is_admin:
            stmt = stmt.where(InterviewRecord.created_by == user_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_scoped(
        self,
        user_id: uuid.UUID,
        is_admin: bool,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[InterviewRecord], int]:
        stmt = select(InterviewRecord).where(InterviewRecord.deleted_at.is_(None))
        if not is_admin:
            stmt = stmt.where(InterviewRecord.created_by == user_id)
        if status is not None:
            stmt = stmt.where(InterviewRecord.status == status)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(InterviewRecord.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def add(self, record: InterviewRecord) -> InterviewRecord:
        self.session.add(record)
        self.session.flush()
        return record
