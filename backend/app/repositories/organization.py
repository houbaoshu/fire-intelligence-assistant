"""Repository for Organization and Department database operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Department, Organization


class OrganizationRepository:
    """Encapsulates all database access for :class:`Organization`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, org_id: str) -> Organization | None:
        """Return a single organization by primary key, excluding soft-deleted."""
        stmt = select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Organization]:
        """Return a paginated list of active, non-deleted organizations."""
        stmt = (
            select(Organization)
            .where(
                Organization.is_active.is_(True),
                Organization.deleted_at.is_(None),
            )
            .order_by(Organization.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        name: str,
        code: str | None = None,
        address: str | None = None,
        contact_phone: str | None = None,
    ) -> Organization:
        """Create and persist a new organization."""
        org = Organization(
            name=name,
            code=code,
            address=address,
            contact_phone=contact_phone,
        )
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def update(
        self,
        org_id: str,
        name: str | None = None,
        code: str | None = None,
        address: str | None = None,
        contact_phone: str | None = None,
        is_active: bool | None = None,
    ) -> Organization | None:
        """Update an organization's fields."""
        org = await self.get_by_id(org_id)
        if org is None:
            return None
        if name is not None:
            org.name = name
        if code is not None:
            org.code = code
        if address is not None:
            org.address = address
        if contact_phone is not None:
            org.contact_phone = contact_phone
        if is_active is not None:
            org.is_active = is_active
        org.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def soft_delete(self, org_id: str) -> bool:
        """Soft-delete an organization by setting deleted_at."""
        org = await self.get_by_id(org_id)
        if org is None:
            return False
        org.deleted_at = datetime.now(UTC)
        org.is_active = False
        await self.db.flush()
        return True


class DepartmentRepository:
    """Encapsulates all database access for :class:`Department`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, dept_id: str) -> Department | None:
        """Return a single department by primary key."""
        stmt = select(Department).where(Department.id == dept_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self, organization_id: str, skip: int = 0, limit: int = 100
    ) -> list[Department]:
        """Return a paginated list of departments for a given organization."""
        stmt = (
            select(Department)
            .where(Department.organization_id == organization_id)
            .order_by(Department.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        organization_id: str,
        name: str,
        parent_id: str | None = None,
    ) -> Department:
        """Create and persist a new department."""
        dept = Department(
            organization_id=organization_id,
            name=name,
            parent_id=parent_id,
        )
        self.db.add(dept)
        await self.db.flush()
        await self.db.refresh(dept)
        return dept
