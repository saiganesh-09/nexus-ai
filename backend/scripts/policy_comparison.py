"""Routing policy comparison — runs the SAME eval dataset under three
policies and reports cost, pass rate, latency and failure rate.

Policies:
  economy     — always the cheapest configured model
  strongest   — always the strongest configured model (tier premium order)
  intelligent — rule-based RoutingEngine per prompt

Usage: python -m scripts.policy_comparison [--tasks N]
Writes backend/eval_reports/policy_comparison_<ts>.json
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.agents.agent import run_agent
from app.core.config import get_settings
from app.database.session import async_session_factory
from app.evaluations.dataset import DATASET
from app.evaluations.scorers import grade, tool_metrics
from app.models import ModelConfig
from app.providers.registry import get_provider
from app.routers.engine import RoutingEngine
from app.services.catalog import estimate_cost_usd

POLICIES = {
    # Ordered candidate lists mirror catalog.TIER_POLICY; first configured wins.
    "economy": [("openai-compatible", "llama3.2:3b")],
    "strongest": [
        ("openai-compatible", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-5"),
        ("openai-compatible", "gpt-4o-mini"),
        ("openai-compatible", "llama3.2:3b"),
    ],
    "intelligent": "engine",
}


def _configured(candidates):
    return [(p, m) for p, m in candidates
            if (inst := get_provider(p)) and inst.is_configured()]


async def _price_map(db) -> dict:
    rows = (await db.execute(select(ModelConfig))).scalars().all()
    return {(r.provider, r.model_id): r for r in rows}


async def run_policy(policy: str, tasks: list[dict], prices: dict) -> dict:
    results = []
    for task in tasks:
        if policy == "intelligent":
            engine = RoutingEngine(
                lambda n: (i := get_provider(n)) is not None and i.is_configured()
            )
            try:
                outcome = engine.decide(task["prompt"])
                candidates = outcome.candidates
            except Exception:
                candidates = _configured(POLICIES["economy"])
        else:
            candidates = _configured(POLICIES[policy])

        agent_run = None
        used = None
        for prov, model in candidates:
            agent_run = await run_agent(task["prompt"], prov, model, max_steps=5)
            used = (prov, model)
            if agent_run.completed or agent_run.provider_error is None:
                break
            # provider_error → try next candidate (fallback)

        ok, score, _ = grade(task["grader"], agent_run.answer if agent_run else None, agent_run)
        passed = ok and agent_run is not None and not agent_run.provider_error
        metrics = tool_metrics(agent_run, task["allowed_tools"]) if agent_run else {}

        cost = 0.0
        entry = prices.get(used) if used else None
        if entry and agent_run and agent_run.input_tokens and agent_run.output_tokens:
            cost = estimate_cost_usd(
                agent_run.input_tokens, agent_run.output_tokens,
                entry.input_price_per_mtok, entry.output_price_per_mtok,
            )

        results.append({
            "task_id": task["id"],
            "passed": passed,
            "score": score,
            "latency_ms": agent_run.latency_ms if agent_run else None,
            "cost_usd": cost,
            "provider_error": agent_run.provider_error if agent_run else "no candidates",
            "model": used[1] if used else None,
            "tools_used": metrics.get("tools_used", []),
        })
        print(f"  [{policy}] {task['id']}: {'PASS' if passed else 'FAIL'} "
              f"({agent_run.latency_ms if agent_run else '?'}ms)", flush=True)

    n = len(results)
    passed_n = sum(r["passed"] for r in results)
    total_cost = sum(r["cost_usd"] for r in results)
    latencies = [r["latency_ms"] for r in results if r["latency_ms"]]
    failures = n - passed_n
    return {
        "policy": policy,
        "tasks": n,
        "passed": passed_n,
        "failed": failures,
        "pass_rate": round(passed_n / n, 4),
        "failure_rate": round(failures / n, 4),
        "total_cost_usd": round(total_cost, 6),
        "cost_per_success_usd": round(total_cost / passed_n, 6) if passed_n else None,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "results": results,
    }


async def main() -> None:
    max_tasks = None
    if "--tasks" in sys.argv:
        max_tasks = int(sys.argv[sys.argv.index("--tasks") + 1])
    tasks = DATASET[:max_tasks] if max_tasks else DATASET

    get_settings()  # ensure env loaded
    async with async_session_factory() as db:
        prices = await _price_map(db)

    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "dataset": f"{len(tasks)} tasks", "policies": {}}
    for policy in POLICIES:
        print(f"=== policy: {policy} ===", flush=True)
        report["policies"][policy] = await run_policy(policy, tasks, prices)
        print(json.dumps({k: v for k, v in report["policies"][policy].items() if k != "results"}, indent=2), flush=True)

    out_dir = Path(__file__).resolve().parent.parent / "eval_reports"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"policy_comparison_{int(time.time())}.json"
    path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written: {path}")


if __name__ == "__main__":
    asyncio.run(main())
