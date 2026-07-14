from __future__ import annotations

from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import create_token, hash_password, verify_password
from app.db.models import AuditLog, User, utc_now
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

_DUMMY_PASSWORD_HASH = hash_password("timing-only-password-value")


class AuthService:
    def __init__(self, session: Session, settings: Settings, signing_key: bytes) -> None:
        self.session = session
        self.settings = settings
        self.signing_key = signing_key
        self.users = UserRepository(session)

    def register(self, payload: RegisterRequest, *, request_id: str | None) -> User:
        if not self.settings.registration_enabled:
            raise AppError(
                status_code=403,
                code="REGISTRATION_DISABLED",
                message="User registration is disabled.",
            )
        email = str(payload.email).lower()
        if self.users.get_by_email(email) is not None:
            raise AppError(
                status_code=409,
                code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email already exists.",
            )
        user = User(
            email=email,
            username=payload.username.strip() if payload.username else None,
            password_hash=hash_password(payload.password),
            role="inspector",
            is_active=True,
        )
        try:
            self.users.add(user)
            self.session.add(
                AuditLog(user_id=user.id, action="user.register", request_id=request_id)
            )
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise AppError(
                status_code=409,
                code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email already exists.",
            ) from error
        return user

    def login(self, payload: LoginRequest, *, request_id: str | None) -> TokenResponse:
        user = self.users.get_by_email(str(payload.email).lower())
        candidate_hash = (
            user.password_hash
            if user is not None and user.password_hash is not None
            else _DUMMY_PASSWORD_HASH
        )
        valid = verify_password(payload.password, candidate_hash)
        if not valid or user is None or not user.is_active:
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="The email or password is incorrect.",
            )
        user.last_login_at = utc_now()
        self.session.add(AuditLog(user_id=user.id, action="user.login", request_id=request_id))
        self.session.commit()
        return TokenResponse(
            access_token=create_token(
                subject=user.id,
                token_type="access",
                lifetime=timedelta(minutes=self.settings.access_token_minutes),
                secret=self.signing_key,
            ),
            refresh_token=create_token(
                subject=user.id,
                token_type="refresh",
                lifetime=timedelta(days=self.settings.refresh_token_days),
                secret=self.signing_key,
            ),
            expires_in=self.settings.access_token_minutes * 60,
        )
