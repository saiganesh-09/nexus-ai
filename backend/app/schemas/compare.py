from pydantic import BaseModel, Field


class CompareRequestIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    # 2+ explicit "provider/model_id" selections; auto-routing is not used.
    models: list[str] = Field(min_length=2, max_length=4)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class CompareResultItem(BaseModel):
    request_id: str
    provider: str
    model: str
    model_display_name: str | None
    content: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    estimated_cost_usd: float | None
    cost_is_estimate: bool
    status: str
    error: str | None


class CompareResponseOut(BaseModel):
    prompt: str
    results: list[CompareResultItem]
