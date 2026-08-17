"""photo_reports 数据访问。业务规则不得出现在此层。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.photo_report import PhotoReport


class PhotoReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_scoped(
        self, report_id: uuid.UUID, creator_ids: list[uuid.UUID] | None
    ) -> PhotoReport | None:
        stmt = (
            select(PhotoReport)
            .options(selectinload(PhotoReport.images))
            .where(PhotoReport.id == report_id, PhotoReport.deleted_at.is_(None))
        )
        if creator_ids is not None:
            stmt = stmt.where(PhotoReport.created_by.in_(creator_ids))
        return self.session.execute(stmt).scalar_one_or_none()

    def list_scoped(
        self,
        creator_ids: list[uuid.UUID] | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PhotoReport], int]:
        stmt = select(PhotoReport).where(PhotoReport.deleted_at.is_(None))
        if creator_ids is not None:
            stmt = stmt.where(PhotoReport.created_by.in_(creator_ids))
        if status is not None:
            stmt = stmt.where(PhotoReport.status == status)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(PhotoReport.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def add(self, report: PhotoReport) -> PhotoReport:
        self.session.add(report)
        self.session.flush()
        return report
