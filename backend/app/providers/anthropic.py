import httpx

from app.core.config import get_settings
from app.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMProviderError,
    ProviderResponse,
)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key
        self.base_url = settings.anthropic_base_url.rstrip("/")
        self.timeout = settings.request_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ProviderResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        chat_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        payload: dict = {
            "model": model,
            "max_tokens": max_tokens or 1024,
            "messages": chat_messages,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        if temperature is not None:
            payload["temperature"] = temperature

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers={
                        "x-api-key": self.api_key or "",
                        "anthropic-version": self.API_VERSION,
                        "Content-Type": "application/json",
                    },
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "anthropic request timed out", provider=self.name, retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"anthropic connection error: {exc}", provider=self.name, retryable=True
            ) from exc

        if resp.status_code >= 400:
            retryable = resp.status_code in (408, 409, 425, 429) or resp.status_code >= 500
            raise LLMProviderError(
                f"anthropic returned HTTP {resp.status_code}: {resp.text[:300]}",
                provider=self.name,
                status_code=resp.status_code,
                retryable=retryable,
            )

        data = resp.json()
        try:
            content = "".join(
                block.get("text", "") for block in data["content"] if block.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise LLMProviderError(
                "anthropic returned malformed response", provider=self.name
            ) from exc

        usage = data.get("usage") or {}
        return ProviderResponse(
            content=content,
            model=data.get("model", model),
            provider="anthropic",
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            raw_usage=usage,
        )
