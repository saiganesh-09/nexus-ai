from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import ModelConfig, User
from app.providers.registry import available_providers, get_provider

router = APIRouter(prefix="/models", tags=["models"])


class ModelOut(BaseModel):
    provider: str
    model_id: str
    display_name: str
    input_price_per_mtok: float
    output_price_per_mtok: float
    context_window: int
    capabilities: dict
    provider_configured: bool


@router.get("", response_model=list[ModelOut])
async def list_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModelOut]:
    rows = (
        await db.execute(
            select(ModelConfig).where(ModelConfig.is_active.is_(True)).order_by(ModelConfig.provider, ModelConfig.model_id)
        )
    ).scalars().all()
    configured = set(available_providers())
    return [
        ModelOut(
            provider=r.provider,
            model_id=r.model_id,
            display_name=r.display_name,
            input_price_per_mtok=r.input_price_per_mtok,
            output_price_per_mtok=r.output_price_per_mtok,
            context_window=r.context_window,
            capabilities=r.capabilities or {},
            provider_configured=r.provider in configured,
        )
        for r in rows
    ]
