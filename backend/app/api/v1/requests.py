import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NexusError
from app.database.session import get_db
from app.models import User
from app.repositories import RequestRepository
from app.schemas.requests import (
    AiRequestDetail,
    AiRequestOut,
    PaginatedRequests,
)

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=PaginatedRequests)
async def list_requests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, max_length=20),
    provider: str | None = Query(default=None, max_length=50),
    model: str | None = Query(default=None, max_length=120),
    request_type: str | None = Query(default=None, max_length=30),
    q: str | None = Query(default=None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRequests:
    repo = RequestRepository(db)
    items, total = await repo.list_paginated(
        current_user.id,
        page=page,
        page_size=page_size,
        status=status,
        provider=provider,
        model=model,
        request_type=request_type,
        q=q,
    )
    return PaginatedRequests(
        items=[AiRequestOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{request_id}", response_model=AiRequestDetail)
async def get_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiRequestDetail:
    repo = RequestRepository(db)
    record = await repo.get_for_user(current_user.id, request_id)
    if record is None:
        raise NexusError(404, "not_found", "Request not found")
    return AiRequestDetail.model_validate(record)
