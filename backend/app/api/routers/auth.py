"""Authentication endpoints (API.md §2)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import CurrentUser, DB, client_ip
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    UserOut,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _login_payload(db, user: User) -> LoginResponse:
    tokens = AuthService(db).issue_tokens(user)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user=UserOut(**user.to_public_dict()),
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DB, request: Request):
    user = AuthService(db).login(payload.email, payload.password)
    AuditService(db).log(
        "user.login", user_id=user.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return _login_payload(db, user)


@router.post("/register", response_model=LoginResponse)
def register(payload: RegisterRequest, db: DB, request: Request):
    user = AuthService(db).register(payload.email, payload.password, payload.full_name)
    AuditService(db).log(
        "user.register", user_id=user.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return _login_payload(db, user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut(**user.to_public_dict())


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, db: DB):
    access_token = AuthService(db).refresh(payload.refresh_token)
    return RefreshResponse(access_token=access_token)
