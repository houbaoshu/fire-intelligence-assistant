"""Permission registry and role-based checks.

Roles (admin/supervisor/inspector/viewer) remain the primary enforcement;
permissions add fine-grained checks that services can require.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models.permission import Permission, RolePermission
from app.models.user import User

# Default permission matrix per role (code -> allowed roles)
DEFAULT_PERMISSIONS: dict[str, list[str]] = {
    "knowledge.upload": ["admin"],
    "knowledge.delete": ["admin"],
    "knowledge.rebuild": ["admin"],
    "record.finalize": ["admin", "supervisor"],
    "record.archive": ["admin", "supervisor"],
    "user.manage": ["admin"],
    "org.manage": ["admin"],
    "audit.view": ["admin"],
    "document.download": ["admin", "supervisor", "inspector", "viewer"],
}


def seed_permissions(db: Session) -> None:
    """Idempotently seed the permission catalog and role matrix."""
    existing = set(db.scalars(select(Permission.code)).all())
    for code in DEFAULT_PERMISSIONS:
        if code not in existing:
            db.add(Permission(code=code, name=code, description=code))
    db.flush()
    matrix: dict[str, set[str]] = {}
    for row in db.scalars(select(RolePermission)).all():
        matrix.setdefault(row.role, set()).add(row.permission_code)
    for code, roles in DEFAULT_PERMISSIONS.items():
        for role in roles:
            if code not in matrix.get(role, set()):
                db.add(RolePermission(role=role, permission_code=code))
    db.flush()


class PermissionService:
    def __init__(self, db: Session):
        self.db = db

    def user_has_permission(self, user: User, code: str) -> bool:
        if user.role == "admin":
            return True
        allowed = self.db.scalar(
            select(RolePermission).where(
                RolePermission.role == user.role,
                RolePermission.permission_code == code,
            )
        )
        return allowed is not None

    def require_permission(self, user: User, code: str) -> None:
        if not self.user_has_permission(user, code):
            raise ForbiddenError(f"权限不足:缺少 {code} 权限")
