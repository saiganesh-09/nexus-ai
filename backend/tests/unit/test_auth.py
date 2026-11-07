import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user, run_async


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture()
def user_a(client: TestClient):
    email = _email("alice")
    data = register_user(client, email, name="Alice")
    return data, auth_headers(client, email)


@pytest.fixture()
def user_b(client: TestClient):
    email = _email("bob")
    data = register_user(client, email, name="Bob")
    return data, auth_headers(client, email)


def test_register_returns_user_without_password_hash(client: TestClient):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "password123", "full_name": "Carol"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "carol@example.com"
    assert "password" not in body and "password_hash" not in body


def test_duplicate_registration_rejected(client: TestClient):
    register_user(client, "dup@example.com")
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "email_taken"


def test_register_weak_password_rejected(client: TestClient):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert res.status_code == 422


def test_login_success_and_invalid(client: TestClient):
    register_user(client, "dave@example.com")
    ok = client.post(
        "/api/v1/auth/login", json={"email": "dave@example.com", "password": "password123"}
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post(
        "/api/v1/auth/login", json={"email": "dave@example.com", "password": "wrong-password"}
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_credentials"


def test_protected_endpoint_rejects_anonymous(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/requests").status_code == 401


def test_me_and_profile_update(client: TestClient, user_a):
    data, headers = user_a
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == data["email"]

    patch = client.patch(
        "/api/v1/users/me", json={"full_name": "Alice Cooper"}, headers=headers
    )
    assert patch.status_code == 200
    assert patch.json()["full_name"] == "Alice Cooper"


def test_logout_revokes_token(client: TestClient, user_a):
    data, headers = user_a
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    # Same token must now be rejected.
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    # A fresh login still works.
    assert client.post(
        "/api/v1/auth/login", json={"email": data["email"], "password": "password123"}
    ).status_code == 200


def test_password_change_revokes_old_token(client: TestClient):
    email = _email("erin")
    register_user(client, email)
    headers = auth_headers(client, email)
    res = client.patch(
        "/api/v1/users/me",
        json={"password": "newpassword456"},
        headers=headers,
    )
    assert res.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    new_headers = auth_headers(client, email, "newpassword456")
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200


def test_password_stored_hashed(client: TestClient):
    from app.database.session import async_session_factory
    from app.models import User
    from sqlalchemy import select

    email = _email("frank")
    register_user(client, email)

    async def fetch():
        async with async_session_factory() as s:
            return (
                await s.execute(select(User).where(User.email == email))
            ).scalar_one()

    user = run_async(fetch())
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")


def test_user_isolation_on_requests(client: TestClient, user_a, user_b):
    from datetime import datetime, timezone

    from app.database.session import async_session_factory
    from app.models import AiRequest, User
    from sqlalchemy import select

    data_b, headers_b = user_b

    async def insert_for_b():
        async with async_session_factory() as s:
            user = (
                await s.execute(select(User).where(User.email == data_b["email"]))
            ).scalar_one()
            req = AiRequest(
                user_id=user.id,
                provider="openai",
                model="gpt-4o-mini",
                prompt="bob secret prompt",
                response_text="bob response",
                status="success",
                created_at=datetime.now(timezone.utc),
            )
            s.add(req)
            await s.commit()
            return req.id

    req_id = run_async(insert_for_b())

    # Bob sees his own request.
    assert client.get(f"/api/v1/requests/{req_id}", headers=headers_b).status_code == 200
    # Alice cannot see it (list and detail).
    _, headers_a = user_a
    assert client.get(f"/api/v1/requests/{req_id}", headers=headers_a).status_code == 404
    listing = client.get("/api/v1/requests", headers=headers_a).json()
    assert listing["total"] == 0
