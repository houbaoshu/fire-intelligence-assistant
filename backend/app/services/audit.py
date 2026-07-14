from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def add_audit_log(
    session: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    record = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        ip_address=ip_address,
        details=details,
    )
    session.add(record)
    return record
