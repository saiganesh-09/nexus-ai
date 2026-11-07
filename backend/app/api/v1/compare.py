from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NexusError
from app.database.session import get_db
from app.models import User
from app.schemas.compare import CompareRequestIn, CompareResponseOut, CompareResultItem
from app.services.chat import ChatService

router = APIRouter(prefix="/compare", tags=["compare"])


@router.post("", response_model=CompareResponseOut)
async def compare_models(
    data: CompareRequestIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompareResponseOut:
    """Fan the same prompt out to explicitly selected models (manual
    selection — auto-routing is bypassed). Each attempt is persisted as its
    own ai_requests row with request_type='comparison'."""
    service = ChatService(db)
    results = []

    for model_choice in data.models:
        try:
            record, response, entry, _ = await service.complete(
                current_user,
                prompt=data.prompt,
                model_choice=model_choice,
                max_tokens=data.max_tokens,
                request_type="comparison",
            )
            results.append(
                CompareResultItem(
                    request_id=str(record.id),
                    provider=record.provider,
                    model=record.model,
                    model_display_name=entry.display_name if entry else None,
                    content=response.content,
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    latency_ms=record.latency_ms,
                    estimated_cost_usd=record.estimated_cost_usd,
                    cost_is_estimate=record.cost_is_estimate,
                    status=record.status,
                    error=record.error_message,
                )
            )
        except NexusError as exc:
            # A failed model must not sink the whole comparison — surface it
            # as an error item alongside the successful ones.
            provider, _, model_id = model_choice.partition("/")
            results.append(
                CompareResultItem(
                    request_id="",
                    provider=provider or model_choice,
                    model=model_id or model_choice,
                    model_display_name=None,
                    content=None,
                    input_tokens=None,
                    output_tokens=None,
                    latency_ms=None,
                    estimated_cost_usd=None,
                    cost_is_estimate=False,
                    status="failed",
                    error=exc.message,
                )
            )

    return CompareResponseOut(prompt=data.prompt, results=results)
