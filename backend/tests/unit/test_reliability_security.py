"""Phase 7 reliability/security tests: cache isolation, rate limiting,
provider retry, credential encryption."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core import cache as cache_mod
from tests.conftest import auth_headers, register_user


@pytest.fixture(autouse=True)
def _reset_cache():
    import asyncio
    asyncio.get_event_loop_policy()
    # Synchronous reset of in-memory fallback for tests.
    cache_mod._memory.clear()
    cache_mod._client_failed = True  # force memory path in tests
    yield
    cache_mod._memory.clear()


@pytest.mark.asyncio
async def test_cache_roundtrip_and_user_isolation():
    await cache_mod.reset_for_tests()
    cache_mod._client_failed = True
    k1 = cache_mod.cache_key("user-a", "p", "m", "hello", None, None)
    k2 = cache_mod.cache_key("user-b", "p", "m", "hello", None, None)
    assert k1 != k2
    await cache_mod.cache_set(k1, {"content": "secret-a"})
    assert (await cache_mod.cache_get(k1))["content"] == "secret-a"
    assert await cache_mod.cache_get(k2) is None


@pytest.mark.asyncio
async def test_cache_expiry():
    cache_mod._client_failed = True
    from app.core.config import get_settings
    settings = get_settings()
    old_ttl = settings.cache_ttl_seconds
    object.__setattr__(settings, "cache_ttl_seconds", -1)
    try:
        k = cache_mod.cache_key("u", "p", "m", "x", None, None)
        await cache_mod.cache_set(k, {"content": "v"})
        # Negative TTL means already expired.
        assert await cache_mod.cache_get(k) is None
    finally:
        object.__setattr__(settings, "cache_ttl_seconds", old_ttl)


def test_chat_second_identical_prompt_is_cache_hit(client: TestClient, monkeypatch):
    """Same prompt+model twice → second request served from cache."""
    from app.providers.base import ProviderResponse

    calls = {"n": 0}

    class FakeProvider:
        name = "openai-compatible"

        def is_configured(self):
            return True

        async def complete(self, messages, model, **kw):
            calls["n"] += 1
            return ProviderResponse(content="cached-answer", model=model,
                                    provider="fake", input_tokens=5, output_tokens=3)

    import app.services.chat as chat_mod
    monkeypatch.setattr(chat_mod, "get_provider", lambda name: FakeProvider())
    cache_mod._memory.clear()
    cache_mod._client_failed = True

    email = f"cache-{uuid.uuid4().hex[:8]}@x.com"
    register_user(client, email)
    headers = auth_headers(client, email)
    payload = {"prompt": "cache me please", "model": "openai-compatible/llama3.2:3b"}

    r1 = client.post("/api/v1/chat", json=payload, headers=headers)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/chat", json=payload, headers=headers)
    assert r2.status_code == 200
    # Provider called once; second served from cache.
    assert calls["n"] == 1
    # Verify via request history that second was a cache hit.
    hist = client.get("/api/v1/requests?page_size=5", headers=headers).json()
    hits = [i for i in hist["items"] if i.get("cache_hit")]
    assert len(hits) == 1


def test_rate_limit_returns_429(client: TestClient):
    "stick with a dedicated app instance to avoid polluting other tests."""
    from app.core.config import get_settings
    settings = get_settings()
    old = settings.rate_limit_requests
    object.__setattr__(settings, "rate_limit_requests", 3)
    try:
        # Unauthenticated requests are limited by IP.
        codes = [client.get("/api/v1/models").status_code for _ in range(5)]
        assert 429 in codes
    finally:
        object.__setattr__(settings, "rate_limit_requests", old)
        from app.middleware import ratelimit as rl
        rl._hits.clear()


def test_provider_retry_on_429(monkeypatch):
    """OpenAI-compatible provider retries retryable HTTP errors."""
    import httpx
    from app.providers.openai_compat import OpenAICompatibleProvider

    attempts = {"n": 0}

    class FakeResp:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": "ok"}}],
                    "model": "m", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    class FakeClient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            attempts["n"] += 1
            if attempts["n"] < 3:
                class ErrResp:
                    status_code = 429
                    text = "rate limited"
                return ErrResp()
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr("asyncio.sleep", lambda *_: _noop())

    async def _run():
        p = OpenAICompatibleProvider(base_url="http://x", api_key=None)
        from app.providers.base import ChatMessage
        return await p.complete([ChatMessage(role="user", content="hi")], "m")

    import asyncio
    resp = asyncio.get_event_loop().run_until_complete(_run()) \
        if False else asyncio.run(_run())
    assert resp.content == "ok"
    assert attempts["n"] == 3


async def _noop():
    return None


def test_credentials_encrypted_and_masked(client: TestClient):
    email = f"cred-{uuid.uuid4().hex[:8]}@x.com"
    register_user(client, email)
    headers = auth_headers(client, email)

    res = client.post("/api/v1/credentials", headers=headers, json={
        "provider": "anthropic", "api_key": "sk-ant-test-secret-12345", "label": "prod",
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert "sk-ant-test-secret" not in str(body)
    assert body["key_preview"].startswith("sk-a")

    # Plaintext must not be in DB.
    import asyncio
    from sqlalchemy import select, text
    from app.database.session import async_session_factory
    from app.models import ApiCredential

    async def _check():
        async with async_session_factory() as s:
            rows = (await s.execute(select(ApiCredential))).scalars().all()
            return rows
    rows = asyncio.run(_check())
    assert all("sk-ant-test-secret" not in r.encrypted_key for r in rows)

    # Other user cannot see/delete it.
    email2 = f"cred2-{uuid.uuid4().hex[:8]}@x.com"
    register_user(client, email2)
    h2 = auth_headers(client, email2)
    assert client.get("/api/v1/credentials", headers=h2).json() == []
    assert client.delete(f"/api/v1/credentials/{body['id']}", headers=h2).status_code == 404


def test_credential_rejects_bad_provider(client: TestClient):
    email = f"cred3-{uuid.uuid4().hex[:8]}@x.com"
    register_user(client, email)
    headers = auth_headers(client, email)
    res = client.post("/api/v1/credentials", headers=headers, json={
        "provider": "evil-provider", "api_key": "x" * 20,
    })
    assert res.status_code == 422
