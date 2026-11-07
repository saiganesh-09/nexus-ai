from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import NexusError
from app.database.session import get_db
from app.evaluations.dataset import DATASET, DATASET_NAME, DATASET_VERSION
from app.evaluations.runner import run_evaluation
from app.models import EvalResult, EvalRun, User

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class RunIn(BaseModel):
    provider: str = "openai-compatible"
    model: str = "llama3.2:3b"
    task_ids: list[str] | None = None
    max_steps: int = Field(default=5, ge=1, le=10)


def _run_out(run: EvalRun, results: list[EvalResult] | None = None) -> dict:
    return {
        "id": str(run.id),
        "dataset_id": str(run.dataset_id),
        "status": run.status,
        "agent_config": run.agent_config,
        "summary": run.summary,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "results": [
            {
                "id": str(r.id),
                "task_id": r.task_id,
                "passed": r.passed,
                "score": r.score,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
                "details": r.details,
            }
            for r in (results or [])
        ],
    }


@router.get("/dataset")
async def get_dataset(current_user: User = Depends(get_current_user)):
    return {
        "name": DATASET_NAME,
        "version": DATASET_VERSION,
        "task_count": len(DATASET),
        "categories": sorted({t["category"] for t in DATASET}),
        "tasks": [
            {"id": t["id"], "category": t["category"], "description": t["description"],
             "allowed_tools": t["allowed_tools"], "prompt": t["prompt"]}
            for t in DATASET
        ],
    }


@router.post("/runs", status_code=201)
async def create_run(
    data: RunIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        run = await run_evaluation(
            db, current_user.id,
            provider=data.provider, model=data.model,
            task_ids=data.task_ids, max_steps=data.max_steps,
        )
    except ValueError as exc:
        raise NexusError(404, "dataset_empty", str(exc)) from exc
    return {"id": str(run.id), "status": run.status, "summary": run.summary}


@router.get("/runs")
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    runs = (
        await db.execute(
            select(EvalRun)
            .where(EvalRun.user_id == current_user.id)
            .order_by(EvalRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    total_count = (await db.execute(
        select(func.count()).select_from(EvalRun).where(EvalRun.user_id == current_user.id)
    )).scalar_one()
    return {
        "items": [_run_out(r) for r in runs],
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total_count // page_size)),
    }


@router.get("/runs/{run_id}")
async def get_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = (
        await db.execute(
            select(EvalRun)
            .where(EvalRun.id == run_id, EvalRun.user_id == current_user.id)
            .options(selectinload(EvalRun.results))
        )
    ).scalar_one_or_none()
    if run is None:
        raise NexusError(404, "run_not_found", "Evaluation run not found")
    return _run_out(run, sorted(run.results, key=lambda r: r.task_id))
