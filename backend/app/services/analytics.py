"""Analytics aggregation — all figures derive from ai_requests rows."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiRequest


def _day(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


async def overview(db: AsyncSession, user_id: UUID, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = select(AiRequest).where(
        AiRequest.user_id == user_id, AiRequest.created_at >= since
    )

    totals = (
        await db.execute(
            select(
                func.count().label("requests"),
                func.coalesce(func.sum(AiRequest.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(AiRequest.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(AiRequest.estimated_cost_usd), 0).label("cost"),
                func.avg(AiRequest.latency_ms).label("avg_latency"),
                func.count().filter(AiRequest.status == "success").label("successes"),
                func.count().filter(AiRequest.cache_hit.is_(True)).label("cache_hits"),
            ).where(AiRequest.user_id == user_id, AiRequest.created_at >= since)
        )
    ).one()

    # Requests + cost per day for the timeseries.
    rows = (
        await db.execute(
            select(AiRequest.created_at, AiRequest.estimated_cost_usd, AiRequest.status)
            .where(AiRequest.user_id == user_id, AiRequest.created_at >= since)
            .order_by(AiRequest.created_at)
        )
    ).all()

    by_day: dict[str, dict] = {}
    for created_at, cost, status in rows:
        d = _day(created_at)
        bucket = by_day.setdefault(d, {"date": d, "requests": 0, "cost": 0.0, "errors": 0})
        bucket["requests"] += 1
        bucket["cost"] += float(cost or 0)
        if status == "failed":
            bucket["errors"] += 1
    timeseries = [by_day[k] for k in sorted(by_day)]

    # Model usage distribution.
    model_rows = (
        await db.execute(
            select(AiRequest.model, func.count().label("count"))
            .where(AiRequest.user_id == user_id, AiRequest.created_at >= since)
            .group_by(AiRequest.model)
            .order_by(func.count().desc())
        )
    ).all()

    total = totals.requests or 0
    return {
        "requests": total,
        "input_tokens": int(totals.input_tokens or 0),
        "output_tokens": int(totals.output_tokens or 0),
        "total_tokens": int((totals.input_tokens or 0) + (totals.output_tokens or 0)),
        "estimated_cost_usd": round(float(totals.cost or 0), 6),
        "avg_latency_ms": round(float(totals.avg_latency or 0), 1),
        "success_rate": round((totals.successes or 0) / total, 4) if total else 0.0,
        "cache_hit_rate": round((totals.cache_hits or 0) / total, 4) if total else 0.0,
        "timeseries": timeseries,
        "model_usage": [{"model": m, "count": c} for m, c in model_rows],
        "window_days": days,
    }


async def by_model(db: AsyncSession, user_id: UUID, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                AiRequest.provider,
                AiRequest.model,
                func.count().label("requests"),
                func.coalesce(func.sum(AiRequest.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(AiRequest.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(AiRequest.estimated_cost_usd), 0).label("cost"),
                func.avg(AiRequest.latency_ms).label("avg_latency"),
                func.count().filter(AiRequest.status == "success").label("successes"),
            )
            .where(AiRequest.user_id == user_id, AiRequest.created_at >= since)
            .group_by(AiRequest.provider, AiRequest.model)
            .order_by(func.count().desc())
        )
    ).all()
    return [
        {
            "provider": r.provider,
            "model": r.model,
            "requests": r.requests,
            "input_tokens": int(r.input_tokens or 0),
            "output_tokens": int(r.output_tokens or 0),
            "estimated_cost_usd": round(float(r.cost or 0), 6),
            "avg_latency_ms": round(float(r.avg_latency or 0), 1),
            "success_rate": round((r.successes or 0) / r.requests, 4) if r.requests else 0.0,
        }
        for r in rows
    ]
