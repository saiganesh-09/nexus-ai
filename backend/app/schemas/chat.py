from pydantic import BaseModel, Field


class ChatRequestIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    # "auto" or omitted → intelligent routing; otherwise "provider/model_id"
    # or a bare model_id that exists in the catalog.
    model: str | None = Field(default=None, max_length=200)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class RoutingInfo(BaseModel):
    complexity_score: float
    complexity_tier: str
    selected_provider: str
    selected_model: str
    reason: str
    signals: list[str]
    policy_version: str
    timestamp: str


class ChatResponseOut(BaseModel):
    id: str
    provider: str
    model: str
    model_display_name: str | None
    content: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    estimated_cost_usd: float | None
    cost_is_estimate: bool
    status: str
    routing: RoutingInfo | None
    error: str | None = None
