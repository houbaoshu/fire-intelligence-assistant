"""Audit logging service.

Only append: never stores passwords, tokens or sensitive document content.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        *,
        user_id: uuid.UUID | str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=uuid.UUID(str(user_id)) if user_id else None,
            action=action,
            entity_type=entity_type,
            entity_id=uuid.UUID(str(entity_id)) if entity_id else None,
            request_id=request_id,
            ip_address=ip_address,
            details=details,
        )
        self.db.add(entry)
        return entry

    def list_recent(self, *, limit: int = 50) -> list[AuditLog]:
        from sqlalchemy import select

        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
