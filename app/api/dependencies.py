from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.bll.account_service import AccountService
from app.dal.account_repository import AccountRepository


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.session_factory() as session:
        yield session


def get_account_service(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> AccountService:
    return AccountService(AccountRepository(session), request.app.state.settings)
