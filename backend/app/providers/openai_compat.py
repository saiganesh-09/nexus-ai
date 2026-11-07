import asyncio

import httpx

from app.core.config import get_settings
from app.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMProviderError,
    ProviderResponse,
)


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI and any OpenAI-compatible /chat/completions endpoint
    (Ollama, Groq, LM Studio, Together, etc.)."""

    name = "openai-compatible"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        display_name: str = "openai-compatible",
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.openai_compat_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.openai_compat_api_key
        self.display_name = display_name
        self.timeout = settings.request_timeout_seconds

    def is_configured(self) -> bool:
        # OpenAI-compatible endpoints may be keyless (e.g. Ollama).
        return bool(self.base_url)

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ProviderResponse:
        payload: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        settings = get_settings()
        self.max_retries = settings.provider_max_retries
        self.retry_base_delay = settings.retry_base_delay_seconds

        last_exc: LLMProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self._request_once(payload, headers, model)
            except LLMProviderError as exc:
                last_exc = exc
                if not exc.retryable or attempt == self.max_retries:
                    raise
                await asyncio.sleep(self.retry_base_delay * (2 ** attempt))
        raise last_exc  # unreachable, satisfies type checkers

    async def _request_once(self, payload: dict, headers: dict, model: str) -> ProviderResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                f"{self.display_name} request timed out", provider=self.name, retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"{self.display_name} connection error: {exc}", provider=self.name, retryable=True
            ) from exc

        if resp.status_code >= 400:
            retryable = resp.status_code in (408, 409, 425, 429) or resp.status_code >= 500
            raise LLMProviderError(
                f"{self.display_name} returned HTTP {resp.status_code}: {resp.text[:300]}",
                provider=self.name,
                status_code=resp.status_code,
                retryable=retryable,
            )

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                f"{self.display_name} returned malformed response",
                provider=self.name,
            ) from exc

        usage = data.get("usage") or {}
        return ProviderResponse(
            content=content,
            model=data.get("model", model),
            provider=self.display_name,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw_usage=usage,
        )
