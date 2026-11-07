from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai_compat import OpenAICompatibleProvider

# "openai-compatible" covers OpenAI, Ollama, Groq, LM Studio and any
# /chat/completions endpoint — configured via OPENAI_COMPAT_BASE_URL /
# OPENAI_COMPAT_API_KEY. Point the base URL at https://api.openai.com/v1
# with a key to use OpenAI itself.
_REGISTRY: dict[str, type[LLMProvider]] = {
    "openai-compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(provider_name: str, **kwargs) -> LLMProvider | None:
    cls = _REGISTRY.get(provider_name)
    if cls is None:
        return None
    return cls(**kwargs)


def available_providers() -> list[str]:
    return [name for name in _REGISTRY if get_provider(name).is_configured()]
