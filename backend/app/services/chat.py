import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NexusError
from app.models import AiRequest, ModelConfig, RequestLog, RoutingDecision, User
from app.providers.base import ChatMessage, LLMProviderError
from app.providers.registry import get_provider
from app.routers.classifier import classify
from app.routers.engine import NoProviderAvailableError, RoutingEngine
from app.services.catalog import (
    MODEL_SEED,
    POLICY_VERSION,
    estimate_cost_usd,
    seed_timestamp,
)


async def seed_model_catalog(db: AsyncSession) -> int:
    """Idempotent catalog seeding — inserts missing provider/model pairs."""
    existing = {
        (r.provider, r.model_id)
        for r in (await db.execute(select(ModelConfig.provider, ModelConfig.model_id))).all()
    }
    added = 0
    for entry in MODEL_SEED:
        if (entry["provider"], entry["model_id"]) in existing:
            continue
        db.add(ModelConfig(**entry, pricing_effective_date=seed_timestamp()))
        added += 1
    if added:
        await db.commit()
    return added


@dataclass
class RouteChoice:
    provider: str
    model_id: str
    classification: object = None
    manual: bool = False
    reason: str = ""
    candidates: list[tuple[str, str]] = None


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _catalog_entry(self, provider: str, model_id: str) -> ModelConfig | None:
        result = await self.db.execute(
            select(ModelConfig).where(
                ModelConfig.provider == provider, ModelConfig.model_id == model_id
            )
        )
        return result.scalar_one_or_none()

    async def resolve_model(self, model_choice: str | None, prompt: str) -> RouteChoice:
        """Decide which provider/model to use, with an explanation."""
        if model_choice and model_choice != "auto":
            if "/" in model_choice:
                provider, model_id = model_choice.split("/", 1)
            else:
                # Bare model id — find it in the catalog.
                result = await self.db.execute(
                    select(ModelConfig).where(ModelConfig.model_id == model_choice)
                )
                entries = result.scalars().all()
                if not entries:
                    raise NexusError(404, "model_not_found", f"Unknown model '{model_choice}'")
                entry = entries[0]
                provider, model_id = entry.provider, entry.model_id
            entry = await self._catalog_entry(provider, model_id)
            if entry is None:
                raise NexusError(404, "model_not_found", f"Model '{model_choice}' is not in the catalog")
            return RouteChoice(
                provider=provider,
                model_id=model_id,
                manual=True,
                reason=f"Manual selection of {provider}/{model_id}",
            )

        classification = classify(prompt)
        engine = RoutingEngine(
            lambda name: (inst := get_provider(name)) is not None and inst.is_configured()
        )
        try:
            outcome = engine.decide(prompt)
        except NoProviderAvailableError as exc:
            raise NexusError(503, "no_provider_available", str(exc)) from exc

        return RouteChoice(
            provider=outcome.provider,
            model_id=outcome.model_id,
            classification=classification,
            reason=outcome.reason,
            candidates=outcome.candidates,
        )

    async def complete(
        self,
        user: User,
        prompt: str,
        model_choice: str | None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        request_type: str = "chat",
    ):
        choice = await self.resolve_model(model_choice, prompt)

        # Auto-routed requests get same-tier fallback across configured
        # candidates; manual selections are single-attempt.
        if choice.manual:
            candidates = [(choice.provider, choice.model_id)]
        else:
            candidates = choice.candidates or [(choice.provider, choice.model_id)]

        record = AiRequest(
            user_id=user.id,
            request_type=request_type,
            provider=choice.provider,
            model=choice.model_id,
            prompt=prompt,
            status="pending",
        )
        self.db.add(record)
        await self.db.flush()

        if choice.classification is not None:
            self.db.add(
                RoutingDecision(
                    request_id=record.id,
                    complexity_score=choice.classification.score,
                    complexity_tier=choice.classification.tier.value,
                    selected_provider=choice.provider,
                    selected_model=choice.model_id,
                    reason=choice.reason,
                    policy_version=POLICY_VERSION,
                )
            )

        messages = [ChatMessage(role="user", content=prompt)]
        last_error: LLMProviderError | None = None
        response = None
        used_provider = used_model = None
        start = time.perf_counter()

        for provider_name, model_id in candidates:
            provider = get_provider(provider_name)
            if provider is None:
                continue
            attempt_start = time.perf_counter()
            self.db.add(
                RequestLog(
                    request_id=record.id,
                    level="info",
                    event="provider_attempt",
                    detail={"provider": provider_name, "model": model_id},
                )
            )
            try:
                response = await provider.complete(
                    messages, model_id, max_tokens=max_tokens, temperature=temperature
                )
                used_provider, used_model = provider_name, model_id
                self.db.add(
                    RequestLog(
                        request_id=record.id,
                        level="info",
                        event="provider_success",
                        detail={
                            "provider": provider_name,
                            "model": response.model,
                            "latency_ms": int((time.perf_counter() - attempt_start) * 1000),
                        },
                    )
                )
                break
            except LLMProviderError as exc:
                last_error = exc
                self.db.add(
                    RequestLog(
                        request_id=record.id,
                        level="error",
                        event="provider_error",
                        detail={
                            "provider": provider_name,
                            "model": model_id,
                            "error": str(exc)[:500],
                            "retryable": exc.retryable,
                        },
                    )
                )
                # Auto-routed requests try every remaining candidate — a
                # model-not-found or transient error on one model should not
                # fail the whole request when another is configured.
                continue

        latency = int((time.perf_counter() - start) * 1000)

        if response is None:
            record.status = "failed"
            record.provider = candidates[-1][0] if candidates else choice.provider
            record.model = candidates[-1][1] if candidates else choice.model_id
            record.latency_ms = latency
            record.error_message = str(last_error)[:1000] if last_error else "no provider available"
            await self.db.commit()
            raise NexusError(
                502,
                "provider_error",
                f"All provider attempts failed. Last error: {record.error_message}",
            )

        record.provider = used_provider
        record.model = used_model

        entry = await self._catalog_entry(used_provider, used_model)
        input_tokens = response.input_tokens
        output_tokens = response.output_tokens
        tokens_estimated = False
        if input_tokens is None or output_tokens is None:
            # Provider did not report usage — estimate and flag it.
            input_tokens = input_tokens if input_tokens is not None else max(1, len(prompt) // 4)
            output_tokens = output_tokens if output_tokens is not None else max(1, len(response.content) // 4)
            tokens_estimated = True

        cost = None
        cost_is_estimate = tokens_estimated
        if entry is not None:
            cost = estimate_cost_usd(
                input_tokens, output_tokens,
                entry.input_price_per_mtok, entry.output_price_per_mtok,
            )

        record.status = "success"
        record.response_text = response.content
        record.input_tokens = input_tokens
        record.output_tokens = output_tokens
        record.latency_ms = latency
        record.estimated_cost_usd = cost
        record.cost_is_estimate = cost_is_estimate
        await self.db.commit()
        await self.db.refresh(record)

        return record, response, entry, choice
