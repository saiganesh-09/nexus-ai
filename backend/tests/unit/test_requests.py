import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


@pytest.fixture()
def headers(client: TestClient):
    email = f"hist-{uuid.uuid4().hex[:8]}@example.com"
    register_user(client, email)
    return auth_headers(client, email)


def test_list_empty(client: TestClient, headers):
    res = client.get("/api/v1/requests", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 0 and body["items"] == []


def test_pagination_validation(client: TestClient, headers):
    assert client.get("/api/v1/requests?page=0", headers=headers).status_code == 422
    assert client.get("/api/v1/requests?page_size=500", headers=headers).status_code == 422


def test_filters_accepted(client: TestClient, headers):
    res = client.get(
        "/api/v1/requests?status=success&provider=openai&model=gpt-4o&q=test",
        headers=headers,
    )
    assert res.status_code == 200
