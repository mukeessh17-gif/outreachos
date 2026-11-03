from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from week4 import auth, auth_routes, models
from week4.main import app


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(test_engine)
    monkeypatch.setattr(auth, "get_engine", lambda: test_engine)
    monkeypatch.setattr(auth_routes, "get_engine", lambda: test_engine)
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-more-than-thirty-two-characters")
    auth._attempts.clear()
    with TestClient(app) as client:
        yield client
    test_engine.dispose()


def test_signup_and_login_hash_password(auth_client: TestClient) -> None:
    signup = auth_client.post(
        "/auth/signup",
        json={
            "email": " Owner@Example.com ",
            "password": "a-very-long-test-password",
            "org_name": "Test Organization",
        },
    )
    assert signup.status_code == 201
    token = signup.json()["access_token"]
    assert auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["org_id"] == signup.json()["org_id"]

    login = auth_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "a-very-long-test-password"},
    )
    assert login.status_code == 200
    assert login.json()["user_id"] == signup.json()["user_id"]


def test_auth_rejects_bad_credentials(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_signup_requires_strong_minimum_password(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/signup",
        json={"email": "a@example.com", "password": "short", "org_name": "Org"},
    )
    assert response.status_code == 422


def test_auth_routes_rate_limit_repeated_failures(auth_client: TestClient) -> None:
    payload = {"email": "missing@example.com", "password": "not-the-password"}
    for _ in range(5):
        assert auth_client.post("/auth/login", json=payload).status_code == 401
    limited = auth_client.post("/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
