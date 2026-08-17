"""认证业务逻辑。router 保持薄，所有规则收敛于此。"""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException, conflict, unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import AuditLog, DEFAULT_ROLE, USER_ROLES, User, UserProfile
from app.repositories.user_repository import AuditLogRepository, UserRepository
from app.schemas.auth import TokenResponse, UserResponse

# 登录失败统一提示，不区分"邮箱不存在"与"密码错误"，防止账号枚举
_INVALID_CREDENTIALS = "邮箱或密码错误"


class AuthService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)
        self.audit = AuditLogRepository(session)
        self.session = session

    def register(
        self, email: str, password: str, full_name: str | None
    ) -> TokenResponse:
        settings = get_settings()
        if not settings.REGISTRATION_ENABLED:
            raise AppException("FORBIDDEN", "注册已关闭", 403)

        if self.users.get_by_email(email) is not None:
            raise conflict("EMAIL_ALREADY_REGISTERED", "该邮箱已注册")

        # 事务：user + profile 一起创建，失败整体回滚
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=DEFAULT_ROLE,
        )
        self.users.create(user)
        self.session.add(UserProfile(user_id=user.id, full_name=full_name))
        self.session.commit()
        self.session.refresh(user)
        return self._issue_tokens(user)

    def login(
        self,
        email: str,
        password: str,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise unauthorized(_INVALID_CREDENTIALS)
        if not user.is_active:
            raise unauthorized(_INVALID_CREDENTIALS)

        self.users.touch_last_login(user)
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="user.login",
                entity_type="user",
                entity_id=user.id,
                request_id=request_id,
                ip_address=ip_address,
            )
        )
        self.session.commit()
        self.session.refresh(user)
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> str:
        user_id = decode_token(refresh_token, "refresh")
        if user_id is None:
            raise unauthorized("refresh_token 无效或已过期")
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise unauthorized("refresh_token 无效或已过期")
        return create_access_token(user.id)

    @staticmethod
    def to_user_response(user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.profile.full_name if user.profile else None,
            role=user.role,
        )

    def _issue_tokens(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            user=self.to_user_response(user),
        )


def is_valid_role(role: str) -> bool:
    return role in USER_ROLES
