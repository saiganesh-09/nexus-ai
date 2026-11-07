"""Redis-backed response cache with graceful in-memory fallback.

Cache keys are user-scoped (user_id is part of the digest) so private
responses can never leak across users. TTL is configurable; if Redis is
unreachable the cache degrades to a process-local dict — never an error.
"""

import hashlib
import json
import time
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

_client: aioredis.Redis | None = None
_client_failed = False
_memory: dict[str, tuple[float, str]] = {}


def _memory_get(key: str) -> str | None:
    item = _memory.get(key)
    if item is None:
        return None
    expires, value = item
    if expires < time.time():
        _memory.pop(key, None)
        return None
    return value


def _memory_set(key: str, value: str, ttl: int) -> None:
    _memory[key] = (time.time() + ttl, value)
    if len(_memory) > 1000:
        # crude bound: drop expired entries
        now = time.time()
        for k in [k for k, (exp, _) in _memory.items() if exp < now]:
            _memory.pop(k, None)


async def _redis() -> aioredis.Redis | None:
    global _client, _client_failed
    if _client_failed:
        return None
    if _client is None:
        try:
            _client = aioredis.from_url(get_settings().redis_url, socket_timeout=2)
            await _client.ping()
        except Exception:
            _client_failed = True
            _client = None
            return None
    return _client


def cache_key(user_id: str, provider: str, model: str, prompt: str,
              max_tokens: int | None, temperature: float | None) -> str:
    raw = json.dumps([user_id, provider, model, prompt, max_tokens, temperature],
                     sort_keys=True)
    return "nexus:chat:" + hashlib.sha256(raw.encode()).hexdigest()


async def cache_get(key: str) -> dict | None:
    client = await _redis()
    if client is not None:
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            pass
    raw = _memory_get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: dict) -> None:
    ttl = get_settings().cache_ttl_seconds
    payload = json.dumps(value)
    client = await _redis()
    if client is not None:
        try:
            await client.set(key, payload, ex=ttl)
            return
        except Exception:
            pass
    _memory_set(key, payload, ttl)


async def reset_for_tests() -> None:
    """Test hook — clears fallback memory and client state."""
    global _client, _client_failed
    _memory.clear()
    _client_failed = False
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
    _client = None
