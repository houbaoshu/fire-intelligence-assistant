"""Organization and department management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.core.exceptions import ConflictException, NotFoundException
from app.core.logging import get_logger
from app.models.user import User
from app.repositories.organization import DepartmentRepository, OrganizationRepository
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)

logger = get_logger(__name__)

router = APIRouter(tags=["organizations"])


@router.get(
    "",
    response_model=list[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all organizations",
)
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """Return a paginated list of organizations. Admin only."""
    repo = OrganizationRepository(db)
    skip = (page - 1) * page_size
    orgs = await repo.list_all(skip=skip, limit=page_size)
    return [OrganizationResponse.model_validate(org) for org in orgs]


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
)
async def create_organization(
    body: OrganizationCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Create a new organization. Admin only."""
    repo = OrganizationRepository(db)

    # Check for duplicate code
    if body.code:
        from sqlalchemy import select

        from app.models.organization import Organization

        existing = await db.execute(select(Organization).where(Organization.code == body.code))
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(f"Organization with code '{body.code}' already exists")

    org = await repo.create(
        name=body.name,
        code=body.code,
        address=body.address,
        contact_phone=body.contact_phone,
    )
    logger.info("Organization created: %s (id=%s) by user %s", org.name, org.id, current_user.id)
    return OrganizationResponse.model_validate(org)


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get organization detail",
)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Return details for a single organization."""
    repo = OrganizationRepository(db)
    org = await repo.get_by_id(org_id)
    if org is None:
        raise NotFoundException(f"Organization '{org_id}' not found")
    return OrganizationResponse.model_validate(org)


@router.put(
    "/{org_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an organization",
)
async def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Update an organization's details. Admin only."""
    repo = OrganizationRepository(db)
    org = await repo.update(
        org_id=org_id,
        name=body.name,
        code=body.code,
        address=body.address,
        contact_phone=body.contact_phone,
        is_active=body.is_active,
    )
    if org is None:
        raise NotFoundException(f"Organization '{org_id}' not found")
    logger.info("Organization updated: %s by user %s", org_id, current_user.id)
    return OrganizationResponse.model_validate(org)


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an organization",
)
async def delete_organization(
    org_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete an organization. Admin only."""
    repo = OrganizationRepository(db)
    deleted = await repo.soft_delete(org_id)
    if not deleted:
        raise NotFoundException(f"Organization '{org_id}' not found")
    logger.info("Organization deleted: %s by user %s", org_id, current_user.id)


# ── Department endpoints ──────────────────────────────────────────────────────


@router.get(
    "/{org_id}/departments",
    response_model=list[DepartmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List departments for an organization",
)
async def list_departments(
    org_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DepartmentResponse]:
    """Return all departments for a given organization."""
    # Verify the organization exists
    org_repo = OrganizationRepository(db)
    org = await org_repo.get_by_id(org_id)
    if org is None:
        raise NotFoundException(f"Organization '{org_id}' not found")

    dept_repo = DepartmentRepository(db)
    skip = (page - 1) * page_size
    departments = await dept_repo.list_by_org(org_id, skip=skip, limit=page_size)
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.post(
    "/{org_id}/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
)
async def create_department(
    org_id: str,
    body: DepartmentCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> DepartmentResponse:
    """Create a new department within an organization. Admin only."""
    # Verify the organization exists
    org_repo = OrganizationRepository(db)
    org = await org_repo.get_by_id(org_id)
    if org is None:
        raise NotFoundException(f"Organization '{org_id}' not found")

    # Verify parent department exists if specified
    if body.parent_id:
        dept_repo = DepartmentRepository(db)
        parent = await dept_repo.get_by_id(body.parent_id)
        if parent is None:
            raise NotFoundException(f"Parent department '{body.parent_id}' not found")

    dept_repo = DepartmentRepository(db)
    dept = await dept_repo.create(
        organization_id=org_id,
        name=body.name,
        parent_id=body.parent_id,
    )
    logger.info(
        "Department created: %s (id=%s) in org %s by user %s",
        dept.name,
        dept.id,
        org_id,
        current_user.id,
    )
    return DepartmentResponse.model_validate(dept)
