"""Generic repository base: thin CRUD/query helpers over SQLAlchemy.

Repositories only encapsulate data access; business rules belong in services.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base

M = TypeVar("M", bound=Base)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseRepository(Generic[M]):
    def __init__(self, db: Session, model: type[M]):
        self.db = db
        self.model = model

    def get(self, obj_id: uuid.UUID | str) -> M | None:
        return self.db.get(self.model, uuid.UUID(str(obj_id)))

    def get_or_404(self, obj_id: uuid.UUID | str) -> M:
        from app.core.exceptions import NotFoundError

        obj = self.get(obj_id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} 不存在")
        return obj

    def list(self, *, limit: int = 20, offset: int = 0, order_by=None) -> list[M]:
        stmt = select(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count(self, *filters) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        for f in filters:
            stmt = stmt.where(f)
        return int(self.db.scalar(stmt) or 0)

    def create(self, **values) -> M:
        obj = self.model(**values)
        self.db.add(obj)
        self.db.flush()
        return obj

    def add(self, obj: M) -> M:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: M, hard: bool = False) -> None:
        if hard:
            self.db.delete(obj)
        elif hasattr(obj, "deleted_at"):
            obj.deleted_at = _utcnow()
        else:
            self.db.delete(obj)
        self.db.flush()

    def flush(self) -> None:
        self.db.flush()
