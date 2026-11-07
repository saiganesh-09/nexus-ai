from datetime import datetime

from pydantic import BaseModel, Field


class RoutingExplainIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class RoutingCandidate(BaseModel):
    provider: str
    model_id: str


class RoutingExplanationOut(BaseModel):
    prompt: str
    complexity_score: float
    complexity_tier: str
    signals: list[str]
    selected_provider: str
    selected_model: str
    reason: str
    policy_version: str
    fallback_candidates: list[RoutingCandidate]
    manual_bypass: bool = False
    decided_at: datetime
