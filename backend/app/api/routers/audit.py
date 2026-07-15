"""Audit log query endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["audit"])


class AuditLogResponse(BaseModel):
    """Response body for a single audit log entry."""

    id: str = Field(..., description="Audit log UUID")
    user_id: str | None = Field(None, description="User who performed the action")
    action: str = Field(..., description="Action performed")
    entity_type: str | None = Field(None, description="Type of entity affected")
    entity_id: str | None = Field(None, description="ID of entity affected")
    request_id: str | None = Field(None, description="Request correlation ID")
    ip_address: str | None = Field(None, description="Client IP address")
    details: dict | None = Field(None, description="Additional details")
    created_at: datetime = Field(..., description="Timestamp of the action")

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/logs",
    response_model=PaginatedResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List audit logs",
)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    start_date: datetime | None = Query(None, description="Filter logs after this date"),
    end_date: datetime | None = Query(None, description="Filter logs before this date"),
    current_user: User = Depends(require_role("admin", "supervisor")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    """Return a paginated list of audit logs with optional filters.

    Only admin and supervisor roles can access audit logs.
    """
    # Build base query with filters
    conditions = []
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if action is not None:
        conditions.append(AuditLog.action == action)
    if entity_type is not None:
        conditions.append(AuditLog.entity_type == entity_type)
    if start_date is not None:
        conditions.append(AuditLog.created_at >= start_date)
    if end_date is not None:
        conditions.append(AuditLog.created_at <= end_date)

    # Count total
    count_stmt = select(func.count()).select_from(AuditLog)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Fetch page
    skip = (page - 1) * page_size
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(page_size)
    if conditions:
        stmt = stmt.where(*conditions)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return PaginatedResponse[AuditLogResponse](
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
