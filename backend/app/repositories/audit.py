"""Repository for AuditLog database operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    """Encapsulates all database access for :class:`AuditLog`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: str | None,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            ip_address=ip_address,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    # ── Read ──────────────────────────────────────────────────────────────

    async def list_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        """Return a paginated list of audit logs for a given user."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
