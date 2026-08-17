"""认证路由（API.md §2）。保持薄：仅解析请求、调用 AuthService。"""

from fastapi import APIRouter, Request

from app.api.dependencies import CurrentUser, DbSession, get_request_id
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, session: DbSession) -> TokenResponse:
    ip = request.client.host if request.client else None
    return AuthService(session).login(
        payload.email,
        payload.password,
        request_id=get_request_id(request),
        ip_address=ip,
    )


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, session: DbSession) -> TokenResponse:
    return AuthService(session).register(
        payload.email, payload.password, payload.full_name
    )


@router.get("/me", response_model=MeResponse)
def me(session: DbSession, current_user: CurrentUser) -> MeResponse:
    base = AuthService.to_user_response(current_user)
    permissions = PermissionService(session).codes_for_role(current_user.role)
    return MeResponse(**base.model_dump(), permissions=permissions)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, session: DbSession) -> RefreshResponse:
    access_token = AuthService(session).refresh(payload.refresh_token)
    return RefreshResponse(access_token=access_token)
