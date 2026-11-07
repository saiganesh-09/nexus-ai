from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import User
from app.schemas.chat import ChatRequestIn, ChatResponseOut, RoutingInfo
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponseOut)
async def chat(
    data: ChatRequestIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponseOut:
    service = ChatService(db)
    record, response, entry, choice = await service.complete(
        current_user,
        prompt=data.prompt,
        model_choice=data.model,
        max_tokens=data.max_tokens,
        temperature=data.temperature,
    )
    routing = None
    if choice.classification is not None:
        from datetime import datetime, timezone

        routing = RoutingInfo(
            complexity_score=choice.classification.score,
            complexity_tier=choice.classification.tier.value,
            selected_provider=choice.provider,
            selected_model=choice.model_id,
            reason=choice.reason,
            signals=choice.classification.signals,
            policy_version="rule-v1",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    return ChatResponseOut(
        id=str(record.id),
        provider=record.provider,
        model=record.model,
        model_display_name=entry.display_name if entry else None,
        content=response.content,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        latency_ms=record.latency_ms or 0,
        estimated_cost_usd=record.estimated_cost_usd,
        cost_is_estimate=record.cost_is_estimate,
        status=record.status,
        routing=routing,
        error=record.error_message,
    )
