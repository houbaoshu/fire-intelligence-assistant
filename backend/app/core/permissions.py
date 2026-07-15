from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.exceptions import AppError
from app.db.models import OrganizationMembership, RolePermission, User
from app.db.session import get_db

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"*"}),
    "supervisor": frozenset(
        {
            "records.read",
            "records.write",
            "records.finalize",
            "documents.download",
            "knowledge.read",
            "knowledge.manage",
            "statistics.read",
            "tasks.manage",
            "audit.read",
        }
    ),
    "inspector": frozenset(
        {
            "records.read",
            "records.write",
            "documents.download",
            "knowledge.read",
            "statistics.read",
            "tasks.manage",
        }
    ),
    "viewer": frozenset(
        {"records.read", "documents.download", "knowledge.read", "statistics.read"}
    ),
}


def has_permission(user: User, permission: str, session: Session | None = None) -> bool:
    if session is not None:
        configured = set(
            session.scalars(
                select(RolePermission.permission).where(RolePermission.role == user.role)
            )
        )
        if configured:
            return "*" in configured or permission in configured
    granted = ROLE_PERMISSIONS.get(user.role, frozenset())
    return "*" in granted or permission in granted


def authorized_user_ids(session: Session, user: User) -> set[uuid.UUID] | None:
    """Return visible creator IDs; None means unrestricted administrator scope."""
    if user.role == "admin":
        return None
    if user.role != "supervisor":
        return {user.id}
    organization_ids = set(
        session.scalars(
            select(OrganizationMembership.organization_id).where(
                OrganizationMembership.user_id == user.id
            )
        )
    )
    if not organization_ids:
        return {user.id}
    member_ids = set(
        session.scalars(
            select(OrganizationMembership.user_id).where(
                OrganizationMembership.organization_id.in_(organization_ids)
            )
        )
    )
    member_ids.add(user.id)
    return member_ids


def require_permission(permission: str) -> Callable[..., User]:
    def dependency(
        user: User = Depends(get_current_user), session: Session = Depends(get_db)
    ) -> User:
        if not has_permission(user, permission, session):
            raise AppError(
                status_code=403,
                code="PERMISSION_DENIED",
                message="You do not have permission to perform this action.",
            )
        return user

    return dependency


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(
            status_code=403,
            code="ADMIN_REQUIRED",
            message="Administrator permission is required.",
        )
    return user
