from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models import User
from app.providers.registry import get_provider
from app.routers.engine import NoProviderAvailableError, RoutingEngine
from app.schemas.routing import (
    RoutingCandidate,
    RoutingExplanationOut,
    RoutingExplainIn,
)

router = APIRouter(prefix="/routing", tags=["routing"])


def _engine() -> RoutingEngine:
    return RoutingEngine(
        lambda name: (inst := get_provider(name)) is not None and inst.is_configured()
    )


@router.post("/explain", response_model=RoutingExplanationOut)
async def explain_routing(
    data: RoutingExplainIn,
    current_user: User = Depends(get_current_user),
) -> RoutingExplanationOut:
    """Return the routing decision for a prompt WITHOUT calling any provider."""
    try:
        outcome = _engine().preview(data.prompt)
    except NoProviderAvailableError as exc:
        from app.core.errors import NexusError

        raise NexusError(503, "no_provider_available", str(exc)) from exc
    return RoutingExplanationOut(
        prompt=data.prompt,
        complexity_score=outcome.score,
        complexity_tier=outcome.tier.value,
        signals=outcome.signals,
        selected_provider=outcome.provider,
        selected_model=outcome.model_id,
        reason=outcome.reason,
        policy_version=outcome.policy_version,
        fallback_candidates=[
            RoutingCandidate(provider=p, model_id=m) for p, m in outcome.candidates[1:]
        ],
        manual_bypass=False,
        decided_at=outcome.decided_at,
    )
