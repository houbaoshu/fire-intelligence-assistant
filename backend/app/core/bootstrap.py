"""启动自动化（M7）：数据库迁移与默认管理员种子。

- ``run_migrations``：应用启动时自动执行 ``alembic upgrade head``（幂等；
  可用 ``AUTO_MIGRATE=false`` 关闭，如测试环境自行迁移）。
- ``seed_default_admin``：``DEFAULT_ADMIN_EMAIL`` / ``DEFAULT_ADMIN_PASSWORD``
  同时设置且邮箱不存在时，幂等创建 ``role=admin`` 用户；密码不落日志。
"""

from pathlib import Path

from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.user import User, UserProfile
from app.repositories.user_repository import UserRepository

logger = get_logger("core.bootstrap")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def run_migrations() -> None:
    settings = get_settings()
    if not settings.AUTO_MIGRATE:
        logger.info("AUTO_MIGRATE=false，跳过启动迁移")
        return
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    logger.info("数据库迁移已就绪（alembic upgrade head）")


def seed_default_admin(session: Session) -> bool:
    """幂等创建默认管理员。返回是否新建（已存在或未配置则不创建）。

    不覆盖既有用户：邮箱已存在时直接跳过，避免重置管理员改过的密码/角色。
    """
    settings = get_settings()
    email = settings.DEFAULT_ADMIN_EMAIL.strip()
    password = settings.DEFAULT_ADMIN_PASSWORD
    if not email or not password:
        return False
    users = UserRepository(session)
    if users.get_by_email(email) is not None:
        logger.info("默认管理员已存在，跳过种子: %s", email)
        return False
    user = User(email=email, password_hash=hash_password(password), role="admin")
    users.create(user)
    session.add(UserProfile(user_id=user.id, full_name="系统管理员"))
    session.commit()
    logger.info("默认管理员已创建: %s", email)
    return True
