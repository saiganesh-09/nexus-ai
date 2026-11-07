"""Routing engine tests — 24 representative prompts across tiers,
provider-configured permutations, fallback ordering and explanations."""

import pytest

from app.routers.classifier import ComplexityTier
from app.routers.engine import NoProviderAvailableError, RoutingEngine
from app.services.catalog import POLICY_VERSION, TIER_POLICY

ALL_PROVIDERS = {"openai-compatible", "anthropic"}
ONLY_LOCAL = {"openai-compatible"}
NONE = set()


def engine_with(configured: set[str]) -> RoutingEngine:
    return RoutingEngine(lambda name: name in configured)


# (prompt, expected_tier) — 8 economy, 8 standard, 8 premium
PROMPT_MATRIX = [
    # --- economy ---
    ("hi", ComplexityTier.ECONOMY),
    ("what is the capital of Japan?", ComplexityTier.ECONOMY),
    ("thanks, that helps!", ComplexityTier.ECONOMY),
    ("define photosynthesis", ComplexityTier.ECONOMY),
    ("who wrote Hamlet?", ComplexityTier.ECONOMY),
    ("is water wet?", ComplexityTier.ECONOMY),
    ("spell necessary", ComplexityTier.ECONOMY),
    ("yes or no: is the sky blue?", ComplexityTier.ECONOMY),
    # --- standard ---
    (
        "Explain how HTTPS handshake works in simple terms for a junior developer.",
        ComplexityTier.STANDARD,
    ),
    (
        "Write a Python function that reverses a linked list and explain it.",
        ComplexityTier.STANDARD,
    ),
    (
        "Compare REST and GraphQL APIs and when to choose each. "
        "Provide concrete examples.",
        ComplexityTier.STANDARD,
    ),
    (
        "Summarize the key differences between TCP and UDP, "
        "including use cases for each protocol.",
        ComplexityTier.STANDARD,
    ),
    (
        "Draft a professional email requesting a deadline extension "
        "from a client, keeping it concise and polite.",
        ComplexityTier.STANDARD,
    ),
    (
        "What are the main causes of the 2008 financial crisis? "
        "List them with brief explanations.",
        ComplexityTier.STANDARD,
    ),
    (
        "Create a SQL query to find the top 10 customers by revenue "
        "in the last quarter, joining orders and customers tables.",
        ComplexityTier.STANDARD,
    ),
    (
        "Explain the concept of recursion with an everyday analogy "
        "and a small code example in JavaScript.",
        ComplexityTier.STANDARD,
    ),
    # --- premium ---
    (
        "Design a distributed rate-limiting service. Analyze consistency "
        "trade-offs, evaluate failure modes, and reason through the "
        "implications for multi-region deployment step by step.",
        ComplexityTier.PREMIUM,
    ),
    (
        "Prove whether P equals NP and discuss the implications "
        "for cryptography and optimization problems.",
        ComplexityTier.PREMIUM,
    ),
    (
        "```python\ndef buggy(x):\n    if x > 0:\n        return buggy(x)\n    return x\n``` "
        "Debug this infinite recursion, refactor it iteratively, "
        "and analyze its time and space complexity.",
        ComplexityTier.PREMIUM,
    ),
    (
        "Architect a multi-tenant SaaS platform handling authentication, "
        "billing, and real-time collaboration. Evaluate Kubernetes vs "
        "serverless trade-offs and justify your design decisions.",
        ComplexityTier.PREMIUM,
    ),
    (
        "Derive the bias-variance tradeoff mathematically, "
        "then evaluate which regularization strategy suits a "
        "high-dimensional sparse dataset and why.",
        ComplexityTier.PREMIUM,
    ),
    (
        "Analyze this production incident: intermittent 502s under load. "
        "```\nnginx upstream timeout\nconnection pool exhausted\n``` "
        "Trace the root cause step by step and propose a remediation plan.",
        ComplexityTier.PREMIUM,
    ),
    (
        "Compare quantum error correction approaches, evaluate their "
        "thresholds, and reason through which is most viable for "
        "near-term fault-tolerant quantum computing.",
        ComplexityTier.PREMIUM,
    ),
    (
        "Design a caching layer for a global e-commerce platform. "
        "Evaluate cache-aside vs write-through vs write-back, analyze "
        "invalidation complexity, and recommend an approach with "
        "detailed trade-off analysis.",
        ComplexityTier.PREMIUM,
    ),
]


@pytest.mark.parametrize("prompt,expected", PROMPT_MATRIX, ids=[f"p{i}" for i in range(len(PROMPT_MATRIX))])
def test_prompt_matrix_tiers(prompt, expected):
    outcome = engine_with(ALL_PROVIDERS).decide(prompt)
    assert outcome.tier == expected, f"{prompt[:50]!r} -> {outcome.tier} (expected {expected})"


def test_tier_distribution_is_mixed():
    tiers = [engine_with(ALL_PROVIDERS).decide(p).tier for p, _ in PROMPT_MATRIX]
    assert tiers.count(ComplexityTier.ECONOMY) >= 5
    assert tiers.count(ComplexityTier.STANDARD) >= 5
    assert tiers.count(ComplexityTier.PREMIUM) >= 5


def test_economy_prefers_local_model():
    outcome = engine_with(ONLY_LOCAL).decide("what is 2+2?")
    assert outcome.provider == "openai-compatible"
    assert outcome.model_id == "llama3.2:3b"


def test_premium_prefers_frontier_then_falls_back():
    outcome = engine_with(ALL_PROVIDERS).decide(PROMPT_MATRIX[-1][0])
    # First premium candidate is gpt-4o via openai-compatible.
    assert outcome.model_id == "gpt-4o"
    # Fallback chain ends with the local model for graceful degradation.
    assert outcome.candidates[-1] == ("openai-compatible", "llama3.2:3b")


def test_fallback_candidates_exclude_unconfigured_providers():
    outcome = engine_with(ONLY_LOCAL).decide(PROMPT_MATRIX[-1][0])
    providers = {p for p, _ in outcome.candidates}
    assert providers == {"openai-compatible"}
    assert all("anthropic" not in p for p, _ in outcome.candidates)


def test_no_provider_raises():
    with pytest.raises(NoProviderAvailableError):
        engine_with(NONE).decide("hello")


def test_reason_contains_score_signals_and_policy():
    outcome = engine_with(ALL_PROVIDERS).decide("```python\ndef f(): pass\n``` debug this")
    assert str(outcome.score) in outcome.reason or f"{outcome.score:.2f}" in outcome.reason
    assert outcome.policy_version == POLICY_VERSION
    assert outcome.signals
    assert "openai-compatible/" in outcome.reason or "anthropic/" in outcome.reason


def test_decision_timestamp_is_set():
    outcome = engine_with(ALL_PROVIDERS).decide("hi")
    assert outcome.decided_at is not None
    assert outcome.decided_at.tzinfo is not None


def test_engine_is_provider_agnostic():
    # Same prompt, same tier regardless of which providers are configured.
    prompt = "Explain how a hash map works."
    a = engine_with(ALL_PROVIDERS).decide(prompt)
    b = engine_with(ONLY_LOCAL).decide(prompt)
    assert a.tier == b.tier
    assert a.score == b.score
