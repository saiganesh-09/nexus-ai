from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AiRequestOut(BaseModel):
    id: UUID
    request_type: str
    provider: str
    model: str
    status: str
    prompt: str
    response_text: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    estimated_cost_usd: float | None
    cost_is_estimate: bool
    cache_hit: bool
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoutingDecisionOut(BaseModel):
    complexity_score: float
    complexity_tier: str
    selected_provider: str
    selected_model: str
    reason: str
    policy_version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AiRequestDetail(AiRequestOut):
    conversation_id: UUID | None
    routing_decision: RoutingDecisionOut | None = None


class PaginatedRequests(BaseModel):
    items: list[AiRequestOut]
    total: int
    page: int
    page_size: int
    pages: int


class RequestQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: str | None = None
    provider: str | None = None
    model: str | None = None
    request_type: str | None = None
    q: str | None = Field(default=None, max_length=200)
    date_from: datetime | None = None
    date_to: datetime | None = None
