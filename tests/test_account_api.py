from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest


def test_register(client, repository):
    user_id = uuid4()
    repository.create.return_value = SimpleNamespace(
        id=user_id, username="alice", password_hash="never-expose-this"
    )
    response = client.post(
        "/account/register", json={"username": "Alice", "password": "strong-password"}
    )
    assert response.status_code == 201
    assert response.json() == {"id": str(user_id), "username": "alice"}


def test_duplicate_register(client, repository):
    repository.get_by_username.return_value = SimpleNamespace(username="alice")
    response = client.post(
        "/account/register", json={"username": "alice", "password": "strong-password"}
    )
    assert response.status_code == 409


@pytest.mark.parametrize("body", [
    {},
    {"username": "ab", "password": "strong-password"},
    {"username": "alice", "password": "short"},
    {"username": "bad name", "password": "strong-password"},
])
def test_invalid_registration(client, repository, body):
    assert client.post("/account/register", json=body).status_code == 422
    repository.create.assert_not_awaited()


def test_get_token(client, service, repository, settings):
    user_id = uuid4()
    repository.get_by_username.return_value = SimpleNamespace(
        id=user_id, password_hash=service.password_hasher.hash("strong-password")
    )
    response = client.post(
        "/account/token", data={"username": "alice", "password": "strong-password"}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    claims = jwt.decode(
        response.json()["access_token"],
        settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"],
    )
    assert claims["sub"] == str(user_id)


def test_invalid_login(client):
    response = client.post(
        "/account/token", data={"username": "missing", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_requires_form_fields(client):
    assert client.post("/account/token", data={}).status_code == 422
