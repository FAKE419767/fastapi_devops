from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UsernameAlreadyExists(Exception):
    pass


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        return await self.session.scalar(select(User).where(User.username == username))

    async def create(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            # PostgreSQL SQLSTATE 23505: unique_violation.
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise UsernameAlreadyExists from exc
            raise
        await self.session.refresh(user)
        return user
