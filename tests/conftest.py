import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.api.dependencies import get_account_service
from app.bll.account_service import AccountService, AccountStorage
from config.settings import Settings

TEST_SECRET = "test-secret-key-for-accounts-at-least-32-characters"


@pytest.fixture
def settings():
    return Settings(_env_file=None, jwt_secret_key=TEST_SECRET)


@pytest.fixture
def repository():
    repository = AsyncMock(spec=AccountStorage)
    repository.get_by_username.return_value = None
    return repository


@pytest.fixture
def service(repository, settings):
    return AccountService(repository, settings)


@pytest.fixture
def client(service, settings, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    from app.main import create_app

    application = create_app(settings)
    application.dependency_overrides[get_account_service] = lambda: service
    with TestClient(application) as client:
        yield client
