from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dal.account_repository import AccountRepository, UsernameAlreadyExists


async def test_duplicate_rolls_back_transaction():
    session = AsyncMock(spec=AsyncSession)
    original = Mock(sqlstate="23505")
    session.commit.side_effect = IntegrityError("insert", {}, original)
    with pytest.raises(UsernameAlreadyExists):
        await AccountRepository(session).create("alice", "hash")
    session.rollback.assert_awaited_once()


async def test_unrelated_integrity_error_is_not_hidden():
    session = AsyncMock(spec=AsyncSession)
    original = Mock(sqlstate="23502")
    session.commit.side_effect = IntegrityError("insert", {}, original)
    with pytest.raises(IntegrityError):
        await AccountRepository(session).create("alice", "hash")
    session.rollback.assert_awaited_once()
