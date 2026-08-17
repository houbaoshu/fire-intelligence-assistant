"""inspection_records 数据访问。业务规则不得出现在此层。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.inspection import InspectionRecord


class InspectionRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_scoped(
        self, record_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool
    ) -> InspectionRecord | None:
        """按数据归属取记录：非 admin 仅可见自己创建的；无权或不存在返回 None。"""
        stmt = (
            select(InspectionRecord)
            .options(selectinload(InspectionRecord.items))
            .where(InspectionRecord.id == record_id, InspectionRecord.deleted_at.is_(None))
        )
        if not is_admin:
            stmt = stmt.where(InspectionRecord.created_by == user_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_scoped(
        self,
        user_id: uuid.UUID,
        is_admin: bool,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[InspectionRecord], int]:
        stmt = select(InspectionRecord).where(InspectionRecord.deleted_at.is_(None))
        if not is_admin:
            stmt = stmt.where(InspectionRecord.created_by == user_id)
        if status is not None:
            stmt = stmt.where(InspectionRecord.status == status)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(InspectionRecord.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def add(self, record: InspectionRecord) -> InspectionRecord:
        self.session.add(record)
        self.session.flush()
        return record
