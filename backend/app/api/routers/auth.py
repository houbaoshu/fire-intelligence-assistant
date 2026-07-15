from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_app_settings, get_current_user, get_signing_key
from app.core.config import Settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    AuthConfigResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/config", response_model=AuthConfigResponse)
def auth_config(settings: Settings = Depends(get_app_settings)) -> AuthConfigResponse:
    return AuthConfigResponse(registration_enabled=settings.registration_enabled)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    signing_key: bytes = Depends(get_signing_key),
) -> User:
    service = AuthService(session, settings, signing_key)
    return service.register(payload, request_id=getattr(request.state, "request_id", None))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    signing_key: bytes = Depends(get_signing_key),
) -> TokenResponse:
    service = AuthService(session, settings, signing_key)
    return service.login(payload, request_id=getattr(request.state, "request_id", None))


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)) -> User:
    return user
