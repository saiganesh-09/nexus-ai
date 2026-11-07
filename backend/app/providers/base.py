from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_usage: dict[str, Any] = field(default_factory=dict)


class LLMProviderError(Exception):
    """Raised when a provider call fails. `retryable` marks transient errors."""

    def __init__(self, message: str, *, provider: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether credentials/config exist to call this provider."""

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ProviderResponse:
        ...
