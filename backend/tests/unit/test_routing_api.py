import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


@pytest.fixture()
def headers(client: TestClient):
    email = f"route-{uuid.uuid4().hex[:8]}@example.com"
    register_user(client, email)
    return auth_headers(client, email)


def test_explain_requires_auth(client: TestClient):
    res = client.post("/api/v1/routing/explain", json={"prompt": "hi"})
    assert res.status_code == 401


def test_explain_returns_full_decision_without_calling_provider(client: TestClient, headers):
    res = client.post(
        "/api/v1/routing/explain",
        json={"prompt": "Explain how TLS certificates work."},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["prompt"] == "Explain how TLS certificates work."
    assert body["complexity_tier"] in ("economy", "standard", "premium")
    assert body["selected_provider"]
    assert body["selected_model"]
    assert body["reason"]
    assert body["policy_version"] == "rule-v1"
    assert body["decided_at"]
    assert isinstance(body["fallback_candidates"], list)
    assert body["manual_bypass"] is False


def test_explain_validates_prompt(client: TestClient, headers):
    res = client.post("/api/v1/routing/explain", json={"prompt": ""}, headers=headers)
    assert res.status_code == 422
