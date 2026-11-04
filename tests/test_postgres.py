import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.dal.account_repository import AccountRepository, UsernameAlreadyExists
from app.models import Base

pytestmark = pytest.mark.integration


async def test_repository_on_postgres():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    if not url.startswith("postgresql+asyncpg://"):
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg://")
    # A unique schema isolates this test from application tables and other runs.
    schema = f"test_{uuid4().hex}"
    admin = create_async_engine(url, poolclass=NullPool)
    engine = None
    try:
        async with admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(
            url, poolclass=NullPool,
            connect_args={"server_settings": {"search_path": schema}},
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            repository = AccountRepository(session)
            user = await repository.create("alice", "password-hash")
            user_id = user.id
        async with factory() as session:
            repository = AccountRepository(session)
            stored = await repository.get_by_username("alice")
            assert stored.id == user_id
            assert stored.password_hash == "password-hash"
            assert stored.created_at is not None
            assert await repository.get_by_username("missing") is None
            with pytest.raises(UsernameAlreadyExists):
                await repository.create("alice", "another-hash")
            assert await repository.get_by_username("alice") is not None
    finally:
        if engine is not None:
            await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin.dispose()
