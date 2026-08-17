"""认证路由（API.md §2）。保持薄：仅解析请求、调用 AuthService。"""

from fastapi import APIRouter, Request

from app.api.dependencies import CurrentUser, DbSession, get_request_id
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

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


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return AuthService.to_user_response(current_user)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, session: DbSession) -> RefreshResponse:
    access_token = AuthService(session).refresh(payload.refresh_token)
    return RefreshResponse(access_token=access_token)
