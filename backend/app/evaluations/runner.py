"""Evaluation runner — executes agent tasks, grades deterministically,
persists EvalDataset/EvalRun/EvalResult rows using the existing schema."""

import json
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent import run_agent
from app.evaluations.dataset import DATASET, DATASET_NAME, DATASET_VERSION
from app.evaluations.scorers import grade, tool_metrics
from app.models import EvalDataset, EvalResult, EvalRun, ModelConfig
from app.services.catalog import estimate_cost_usd


async def _ensure_dataset(db: AsyncSession, user_id: UUID) -> EvalDataset:
    result = await db.execute(select(EvalDataset).where(EvalDataset.name == DATASET_NAME))
    ds = result.scalar_one_or_none()
    if ds is None:
        ds = EvalDataset(
            name=DATASET_NAME,
            description="Core agent tool-use evaluation set (deterministic graders)",
            version=DATASET_VERSION,
            tasks=DATASET,
            created_by=user_id,
        )
        db.add(ds)
        await db.flush()
    return ds


async def _model_entry(db: AsyncSession, provider: str, model: str) -> ModelConfig | None:
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.provider == provider, ModelConfig.model_id == model)
    )
    return result.scalar_one_or_none()


async def run_evaluation(
    db: AsyncSession,
    user_id: UUID,
    *,
    provider: str = "openai-compatible",
    model: str = "llama3.2:3b",
    task_ids: list[str] | None = None,
    max_steps: int = 5,
) -> EvalRun:
    dataset = await _ensure_dataset(db, user_id)
    tasks = [t for t in DATASET if task_ids is None or t["id"] in task_ids]
    if not tasks:
        raise ValueError("no matching evaluation tasks")

    entry = await _model_entry(db, provider, model)
    run = EvalRun(
        dataset_id=dataset.id,
        user_id=user_id,
        agent_config={
            "provider": provider,
            "model": model,
            "max_steps": max_steps,
            "dataset_version": DATASET_VERSION,
        },
        status="running",
        summary={},
    )
    db.add(run)
    await db.flush()

    passed = 0
    total_score = 0.0
    by_category: dict[str, dict] = {}
    start = time.perf_counter()

    for task in tasks:
        agent_run = await run_agent(task["prompt"], provider, model, max_steps=max_steps)
        ok, score, gdetails = grade(task["grader"], agent_run.answer, agent_run)
        metrics = tool_metrics(agent_run, task["allowed_tools"])
        task_passed = ok and not agent_run.provider_error
        passed += int(task_passed)
        total_score += score

        cat = by_category.setdefault(task["category"], {"total": 0, "passed": 0})
        cat["total"] += 1
        cat["passed"] += int(task_passed)

        cost = None
        if entry and agent_run.input_tokens is not None and agent_run.output_tokens is not None:
            cost = estimate_cost_usd(
                agent_run.input_tokens, agent_run.output_tokens,
                entry.input_price_per_mtok, entry.output_price_per_mtok,
            )

        db.add(EvalResult(
            run_id=run.id,
            task_id=task["id"],
            passed=task_passed,
            score=score,
            latency_ms=agent_run.latency_ms or None,
            cost_usd=cost,
            details={
                "category": task["category"],
                "description": task["description"],
                "prompt": task["prompt"],
                "grader": task["grader"],
                "grader_details": gdetails,
                "answer": agent_run.answer,
                "completed": agent_run.completed,
                "provider_error": agent_run.provider_error,
                "input_tokens": agent_run.input_tokens,
                "output_tokens": agent_run.output_tokens,
                "tools": metrics,
                "trace": [s.__dict__ for s in agent_run.steps],
            },
        ))
        await db.commit()  # incremental persistence

    duration = int((time.perf_counter() - start) * 1000)
    n = len(tasks)
    run.status = "completed"
    run.summary = {
        "total_tasks": n,
        "passed_tasks": passed,
        "failed_tasks": n - passed,
        "pass_rate": round(passed / n, 4),
        "avg_score": round(total_score / n, 4),
        "duration_ms": duration,
        "by_category": by_category,
        "scoring": "deterministic graders only — no LLM judge",
    }
    await db.commit()
    await db.refresh(run)
    return run
