"""Model catalog seed data and routing policy.

Pricing is USD per 1M tokens, effective as of the seed date. Values are
public list prices and must be kept current — they are estimates for
cost display, not provider-billed amounts.
"""

from datetime import datetime, timezone

MODEL_SEED = [
    # Local / OpenAI-compatible (Ollama etc.) — keyless, $0 list price.
    {
        "provider": "openai-compatible",
        "model_id": "llama3.2:3b",
        "display_name": "Llama 3.2 3B (local)",
        "input_price_per_mtok": 0.0,
        "output_price_per_mtok": 0.0,
        "context_window": 131072,
        "capabilities": {"streaming": True, "tools": False, "local": True},
    },
    # OpenAI via the compatible endpoint (set OPENAI_COMPAT_BASE_URL to
    # https://api.openai.com/v1 and OPENAI_COMPAT_API_KEY to enable).
    {
        "provider": "openai-compatible",
        "model_id": "gpt-4o-mini",
        "display_name": "GPT-4o mini",
        "input_price_per_mtok": 0.15,
        "output_price_per_mtok": 0.60,
        "context_window": 128000,
        "capabilities": {"streaming": True, "tools": True},
    },
    {
        "provider": "openai-compatible",
        "model_id": "gpt-4o",
        "display_name": "GPT-4o",
        "input_price_per_mtok": 2.50,
        "output_price_per_mtok": 10.00,
        "context_window": 128000,
        "capabilities": {"streaming": True, "tools": True},
    },
    # Anthropic native API.
    {
        "provider": "anthropic",
        "model_id": "claude-3-5-haiku-latest",
        "display_name": "Claude 3.5 Haiku",
        "input_price_per_mtok": 0.80,
        "output_price_per_mtok": 4.00,
        "context_window": 200000,
        "capabilities": {"streaming": True, "tools": True},
    },
    {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-5",
        "display_name": "Claude Sonnet 4.5",
        "input_price_per_mtok": 3.00,
        "output_price_per_mtok": 15.00,
        "context_window": 200000,
        "capabilities": {"streaming": True, "tools": True},
    },
]

POLICY_VERSION = "rule-v1"

# Ordered candidate lists per tier; the router picks the first whose
# provider is configured. Local models are deliberately cheapest-first.
TIER_POLICY: dict[str, list[tuple[str, str]]] = {
    "economy": [
        ("openai-compatible", "llama3.2:3b"),
        ("openai-compatible", "gpt-4o-mini"),
        ("anthropic", "claude-3-5-haiku-latest"),
    ],
    "standard": [
        ("openai-compatible", "gpt-4o-mini"),
        ("openai-compatible", "llama3.2:3b"),
        ("anthropic", "claude-3-5-haiku-latest"),
    ],
    "premium": [
        ("openai-compatible", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-5"),
        ("openai-compatible", "gpt-4o-mini"),
        # Graceful degradation: weakest configured model beats total failure.
        ("openai-compatible", "llama3.2:3b"),
    ],
}


def estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    input_price_per_mtok: float,
    output_price_per_mtok: float,
) -> float | None:
    """Estimated USD cost. Returns None when token counts are unavailable."""
    if input_tokens is None or output_tokens is None:
        return None
    return round(
        (input_tokens * input_price_per_mtok + output_tokens * output_price_per_mtok)
        / 1_000_000,
        6,
    )


def seed_timestamp() -> datetime:
    return datetime.now(timezone.utc)
