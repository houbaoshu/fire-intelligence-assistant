from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user
