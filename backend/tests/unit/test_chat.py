import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user

from app.providers.base import ProviderResponse


class FakeProvider:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = []

    def is_configured(self):
        return True

    async def complete(self, messages, model, **kwargs):
        self.calls.append((messages, model))
        if self.fail:
            from app.providers.base import LLMProviderError

            raise LLMProviderError("boom", provider="fake", status_code=500, retryable=True)
        return ProviderResponse(
            content="fake response",
            model=model,
            provider="fake",
            input_tokens=10,
            output_tokens=5,
            raw_usage={},
        )


@pytest.fixture()
def headers(client: TestClient):
    email = f"chat-{uuid.uuid4().hex[:8]}@example.com"
    register_user(client, email)
    return auth_headers(client, email)


def test_chat_requires_auth(client: TestClient):
    res = client.post("/api/v1/chat", json={"prompt": "hello"})
    assert res.status_code == 401


def test_chat_persists_request_and_reports_usage(client: TestClient, headers, monkeypatch):
    from app.providers import registry
    from app.services import chat as chat_module

    fake = FakeProvider()
    monkeypatch.setattr(registry, "get_provider", lambda name, **kw: fake)
    monkeypatch.setattr(chat_module, "get_provider", lambda name, **kw: fake)

    res = client.post(
        "/api/v1/chat",
        json={"prompt": "Explain quantum computing briefly.", "model": "openai-compatible/llama3.2:3b"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "success"
    assert body["content"] == "fake response"
    assert body["input_tokens"] == 10 and body["output_tokens"] == 5
    assert body["latency_ms"] >= 0
    assert body["id"]

    # The request must be visible in history.
    history = client.get("/api/v1/requests", headers=headers).json()
    assert history["total"] == 1
    assert history["items"][0]["id"] == body["id"]


def test_chat_auto_routing_returns_explanation(client: TestClient, headers, monkeypatch):
    from app.providers import registry
    from app.services import chat as chat_module

    fake = FakeProvider()
    monkeypatch.setattr(registry, "get_provider", lambda name, **kw: fake)
    monkeypatch.setattr(chat_module, "get_provider", lambda name, **kw: fake)

    res = client.post(
        "/api/v1/chat",
        json={"prompt": "hi", "model": "auto"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["routing"] is not None
    assert body["routing"]["complexity_tier"] == "economy"
    assert "rule" in body["routing"]["policy_version"] or body["routing"]["policy_version"]


def test_chat_provider_failure_recorded(client: TestClient, headers, monkeypatch):
    from app.providers import registry
    from app.services import chat as chat_module

    fake = FakeProvider(fail=True)
    monkeypatch.setattr(registry, "get_provider", lambda name, **kw: fake)
    monkeypatch.setattr(chat_module, "get_provider", lambda name, **kw: fake)

    res = client.post(
        "/api/v1/chat",
        json={"prompt": "hello", "model": "openai-compatible/llama3.2:3b"},
        headers=headers,
    )
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "provider_error"

    history = client.get("/api/v1/requests?status=failed", headers=headers).json()
    assert history["total"] == 1
    assert history["items"][0]["status"] == "failed"


def test_models_endpoint_lists_catalog(client: TestClient, headers):
    res = client.get("/api/v1/models", headers=headers)
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 3
    assert all("provider_configured" in m for m in models)
