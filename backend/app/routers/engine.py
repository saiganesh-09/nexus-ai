"""Dedicated model-routing engine.

Provider-independent: the engine never imports provider clients. Callers
inject which providers are configured; the engine returns a routing
decision (provider, model, explanation, candidate fallback order) that the
chat service executes.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.routers.classifier import ComplexityTier, Classification, classify
from app.services.catalog import POLICY_VERSION, TIER_POLICY


@dataclass
class RoutingOutcome:
    provider: str
    model_id: str
    tier: ComplexityTier
    score: float
    signals: list[str]
    reason: str
    policy_version: str
    candidates: list[tuple[str, str]] = field(default_factory=list)
    manual: bool = False
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NoProviderAvailableError(Exception):
    pass


class RoutingEngine:
    """Rule-based routing policy executor.

    `is_configured(provider_name)` is injected so the engine stays decoupled
    from provider credential details.
    """

    POLICY_VERSION = POLICY_VERSION

    def __init__(self, is_configured: Callable[[str], bool]):
        self._is_configured = is_configured

    def _configured_candidates(self, tier: ComplexityTier) -> list[tuple[str, str]]:
        return [
            (p, m)
            for p, m in TIER_POLICY[tier.value]
            if self._is_configured(p)
        ]

    def decide(self, prompt: str) -> RoutingOutcome:
        """Classify `prompt` and pick the best configured model."""
        classification: Classification = classify(prompt)
        candidates = self._configured_candidates(classification.tier)
        if not candidates:
            raise NoProviderAvailableError(
                "No LLM provider is configured for any routing tier."
            )

        provider, model_id = candidates[0]
        reason = (
            f"Rule-based classifier scored {classification.score:.2f} "
            f"({classification.tier.value}) from signals "
            f"{', '.join(classification.signals) or 'none'}; "
            f"policy {self.POLICY_VERSION} selected {provider}/{model_id} "
            f"as the first of {len(candidates)} configured candidate(s) "
            f"for tier '{classification.tier.value}'."
        )
        return RoutingOutcome(
            provider=provider,
            model_id=model_id,
            tier=classification.tier,
            score=classification.score,
            signals=classification.signals,
            reason=reason,
            policy_version=self.POLICY_VERSION,
            candidates=candidates,
        )

    def preview(self, prompt: str) -> RoutingOutcome:
        """Same as decide() — exposed separately for the explain API so the
        intent ('what would happen') is explicit at call sites."""
        return self.decide(prompt)
