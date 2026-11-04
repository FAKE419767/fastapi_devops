from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest

from app.bll.account_service import AccountConflict, InvalidCredentials
from app.dal.account_repository import UsernameAlreadyExists


async def test_registration_hashes_password(service, repository):
    repository.create.return_value = SimpleNamespace(id=uuid4(), username="alice")
    user = await service.register("Alice", "strong-password")
    assert user.username == "alice"
    username, password_hash = repository.create.call_args.args
    assert username == "alice"
    assert password_hash != "strong-password"
    assert service.password_hasher.verify("strong-password", password_hash)


async def test_duplicate_registration(service, repository):
    repository.get_by_username.return_value = SimpleNamespace(username="alice")
    with pytest.raises(AccountConflict):
        await service.register("Alice", "strong-password")
    repository.create.assert_not_awaited()


async def test_concurrent_duplicate_registration(service, repository):
    repository.create.side_effect = UsernameAlreadyExists
    with pytest.raises(AccountConflict):
        await service.register("alice", "strong-password")


async def test_login_issues_signed_expiring_jwt(service, repository, settings):
    user_id = uuid4()
    repository.get_by_username.return_value = SimpleNamespace(
        id=user_id, password_hash=service.password_hasher.hash("strong-password")
    )
    token = await service.login("Alice", "strong-password")
    claims = jwt.decode(
        token.access_token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"]
    )
    assert claims["sub"] == str(user_id)
    assert claims["exp"] - claims["iat"] == settings.access_token_expire_minutes * 60
    assert token.token_type == "bearer"
    repository.get_by_username.assert_awaited_once_with("alice")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token.access_token, "wrong-secret-key-with-32-characters", algorithms=["HS256"])


@pytest.mark.parametrize("exists", [True, False])
async def test_invalid_credentials(service, repository, exists):
    if exists:
        repository.get_by_username.return_value = SimpleNamespace(
            password_hash=service.password_hasher.hash("correct-password")
        )
    with pytest.raises(InvalidCredentials):
        await service.login("alice", "wrong-password")


def test_expired_jwt_is_rejected(settings):
    secret = settings.jwt_secret_key.get_secret_value()
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        secret, algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, secret, algorithms=["HS256"])
