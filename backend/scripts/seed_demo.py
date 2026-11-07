"""Seed realistic demo data into ai_requests (+ routing decisions, logs,
eval run) for the dashboard/history/analytics pages.

- Idempotent: deletes prior seeded rows for the target user first.
- Honest: every row is a stored DB record; dashboard metrics are derived
  from them by the real analytics queries. Rows are marked
  metadata={"seeded": true} so demo data is distinguishable.
- Usage: python -m scripts.seed_demo [--email user@x.com] [--reset]
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.database.session import async_session_factory
from app.models import (
    AiRequest, EvalResult, EvalRun, RequestLog, RoutingDecision, User,
)
from app.routers.classifier import classify
from app.services.catalog import estimate_cost_usd

random.seed(42)

PROMPTS = [
    ("What is the time complexity of binary search?", "llama3.2:3b", 0.9),
    ("Explain HTTPS handshake in simple terms", "llama3.2:3b", 1.4),
    ("Write a Python function to check if a string is a palindrome", "llama3.2:3b", 1.8),
    ("Compare REST vs GraphQL for a mobile app backend", "gpt-4o-mini", 2.4),
    ("Design a rate limiter for a public API", "gpt-4o", 3.6),
    ("Debug this infinite loop: while x>0: x=x+1", "llama3.2:3b", 2.0),
    ("Summarize the CAP theorem for distributed systems", "gpt-4o-mini", 2.2),
    ("What are the main causes of inflation?", "llama3.2:3b", 1.6),
    ("Create a SQL query for top 10 customers by revenue", "llama3.2:3b", 2.1),
    ("Explain quantum entanglement to a 10-year-old", "llama3.2:3b", 1.9),
    ("Refactor this React component to use hooks", "gpt-4o-mini", 2.6),
    ("Prove that sqrt(2) is irrational", "gpt-4o", 3.2),
    ("What is the capital of Australia?", "llama3.2:3b", 0.5),
    ("Translate 'good morning' to Japanese", "llama3.2:3b", 0.7),
    ("Analyze trade-offs of microservices vs monolith", "gpt-4o", 3.9),
    ("Write unit tests for a debounce function", "gpt-4o-mini", 2.5),
    ("How does TCP congestion control work?", "gpt-4o-mini", 2.3),
    ("Draft a professional email requesting a deadline extension", "llama3.2:3b", 1.5),
    ("What is machine learning? Explain with examples", "llama3.2:3b", 2.0),
    ("Optimize this Python code for memory usage", "gpt-4o-mini", 2.7),
    ("Explain the difference between process and thread", "llama3.2:3b", 1.7),
    ("Design a URL shortener system at scale", "gpt-4o", 4.1),
    ("What is the boiling point of ethanol?", "llama3.2:3b", 0.6),
    ("Compare Python and Go for backend services", "gpt-4o-mini", 2.8),
    ("Implement a LRU cache in Python", "gpt-4o-mini", 2.9),
]

RESPONSES = {
    "llama3.2:3b": "Here's a clear explanation. {topic} works by {mechanism}. In practice, you should consider {caveat} when applying it. Would you like a code example?",
    "gpt-4o-mini": "{topic} can be understood through three lenses: correctness, performance, and maintainability. First, {detail}. Second, watch for {pitfall}. Finally, measure before optimizing.",
    "gpt-4o": "## Analysis\n\n{topic} involves several interacting concerns. Let me break this down systematically.\n\n**Core idea:** {detail}\n\n**Trade-offs:** {tradeoff}\n\n**Recommendation:** Start simple, instrument early, and iterate based on measured bottlenecks rather than assumptions.",
}

PRICES = {
    ("openai-compatible", "llama3.2:3b"): (0.0, 0.0),
    ("openai-compatible", "gpt-4o-mini"): (0.15, 0.60),
    ("openai-compatible", "gpt-4o"): (2.50, 10.00),
}

TOPICS = ["the approach", "this pattern", "the algorithm", "the design", "the concept"]
MECHANISMS = ["breaking the problem into smaller parts", "balancing trade-offs", "applying well-known heuristics", "iterating with feedback"]
CAVEATS = ["edge cases", "scale", "latency budgets", "team familiarity"]
DETAILS = ["start with the simplest correct implementation", "profile before optimizing", "prefer composition over inheritance", "keep the API surface small"]
PITFALLS = ["premature optimization", "ignoring failure modes", "over-engineering", "skipping tests"]
TRADEOFFS = ["latency vs. consistency", "cost vs. quality", "simplicity vs. flexibility", "speed vs. correctness"]


def _fill(template: str) -> str:
    return (template
            .replace("{topic}", random.choice(TOPICS))
            .replace("{mechanism}", random.choice(MECHANISMS))
            .replace("{caveat}", random.choice(CAVEATS))
            .replace("{detail}", random.choice(DETAILS))
            .replace("{pitfall}", random.choice(PITFALLS))
            .replace("{tradeoff}", random.choice(TRADEOFFS)))


async def seed(email: str | None, reset: bool) -> None:
    async with async_session_factory() as db:
        q = select(User)
        if email:
            q = q.where(User.email == email)
        user = (await db.execute(q.order_by(User.created_at))).scalars().first()
        if user is None:
            print("No user found — register one first or pass --email")
            return
        print(f"Seeding for user: {user.email} ({user.id})")

        # Idempotency: remove previously seeded rows for this user.
        old_ids = list((await db.execute(
            select(AiRequest.id).where(AiRequest.user_id == user.id)
        )).scalars().all())
        if old_ids:
            meta_rows = (await db.execute(
                select(AiRequest.id, AiRequest.metadata_).where(AiRequest.id.in_(old_ids))
            )).all()
            seeded_ids = [i for i, m in meta_rows if (m or {}).get("seeded")]
            if seeded_ids:
                await db.execute(delete(RequestLog).where(RequestLog.request_id.in_(seeded_ids)))
                await db.execute(delete(RoutingDecision).where(RoutingDecision.request_id.in_(seeded_ids)))
                await db.execute(delete(AiRequest).where(AiRequest.id.in_(seeded_ids)))
                await db.commit()
                print(f"Removed {len(seeded_ids)} previously seeded requests")

        now = datetime.now(timezone.utc)
        created = 0
        VARIANTS = ["", "please", "for me", "quickly", "in detail", "step by step"]
        items = [(p, m, w) for p, m, w in PROMPTS for _ in range(2)]
        random.shuffle(items)
        for i, (prompt, model, weight) in enumerate(items[:50]):
            prompt = f"{prompt} {VARIANTS[i % len(VARIANTS)]}".strip()
            # Spread across last 30 days, weighted toward recent.
            days_ago = int(30 * (1 - (i / len(PROMPTS)) ** 0.7)) + random.randint(0, 2)
            ts = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            provider = "openai-compatible"
            in_tok = random.randint(20, 400)
            out_tok = random.randint(60, int(1400 * weight))
            latency = int(400 + 2200 * weight + random.randint(-150, 350))
            pin, pout = PRICES.get((provider, model), (0.0, 0.0))
            cost = estimate_cost_usd(in_tok, out_tok, pin, pout)
            status = "failed" if random.random() < 0.03 else "success"
            cache_hit = status == "success" and random.random() < 0.21
            is_auto = random.random() < 0.65
            req_type = "comparison" if i % 11 == 5 else "chat"

            rec = AiRequest(
                user_id=user.id, request_type=req_type, provider=provider,
                model=model, prompt=prompt,
                response_text=_fill(RESPONSES[model]) if status == "success" else None,
                status=status, input_tokens=in_tok if status == "success" else None,
                output_tokens=out_tok if status == "success" else None,
                latency_ms=latency if status == "success" else latency,
                estimated_cost_usd=cost if status == "success" else None,
                cost_is_estimate=False, cache_hit=cache_hit,
                error_message="provider timeout" if status == "failed" else None,
                metadata_={"seeded": True, "routing": "auto" if is_auto else "manual"},
            )
            # Timestamp override: server_default sets now(); set explicitly.
            rec.created_at = ts
            db.add(rec)
            await db.flush()

            if is_auto and status == "success":
                c = classify(prompt)
                db.add(RoutingDecision(
                    request_id=rec.id,
                    complexity_score=c.score, complexity_tier=c.tier.value,
                    selected_provider=provider, selected_model=model,
                    reason=f"Rule-based classifier scored {c.score:.2f} ({c.tier.value}); policy rule-v1.",
                    policy_version="rule-v1",
                ))
            db.add(RequestLog(
                request_id=rec.id, level="info" if status == "success" else "error",
                event="provider_success" if status == "success" else "provider_error",
                detail={"provider": provider, "model": model, "seeded": True},
            ))
            created += 1

        # One seeded eval run marked clearly as demo.
        eval_run = EvalRun(
            dataset_id=None, user_id=user.id,  # dataset_id nullable? FK — use existing or skip
            agent_config={"provider": provider, "model": "llama3.2:3b", "seeded": True},
            status="completed",
            summary={"seeded": True, "note": "Demo evaluation record — not a real run",
                     "total_tasks": 25, "passed_tasks": 17, "failed_tasks": 8,
                     "pass_rate": 0.68, "avg_score": 0.72, "duration_ms": 95000,
                     "by_category": {"calculator": {"total": 6, "passed": 5},
                                     "knowledge": {"total": 7, "passed": 6},
                                     "code_analysis": {"total": 6, "passed": 4},
                                     "reasoning": {"total": 6, "passed": 2}},
                     "scoring": "deterministic graders only — seeded demo"},
        )
        # dataset_id is non-nullable FK; fetch or create dataset row.
        from app.models import EvalDataset
        ds = (await db.execute(select(EvalDataset).where(EvalDataset.name == "core-agent-eval"))).scalar_one_or_none()
        if ds is None:
            from app.evaluations.dataset import DATASET, DATASET_NAME, DATASET_VERSION
            ds = EvalDataset(name=DATASET_NAME, description="core", version=DATASET_VERSION,
                             tasks=DATASET, created_by=user.id)
            db.add(ds)
            await db.flush()
        eval_run.dataset_id = ds.id
        db.add(eval_run)
        await db.flush()
        for tid, cat, passed, score in [
            ("calc-01", "calculator", True, 1.0), ("know-01", "knowledge", True, 1.0),
            ("code-03", "code_analysis", True, 1.0), ("mix-02", "reasoning", False, 0.0),
        ]:
            db.add(EvalResult(run_id=eval_run.id, task_id=tid, passed=passed, score=score,
                              latency_ms=random.randint(1500, 6000), cost_usd=0.0,
                              details={"seeded": True, "category": cat,
                                       "description": f"Seeded demo task {tid}",
                                       "prompt": "(seeded)", "answer": "(seeded demo)"}))
        await db.commit()
        print(f"Seeded {created} requests + 1 demo eval run for {user.email}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--email")
    ap.add_argument("--reset", action="store_true", help="clear seeded rows first")
    args = ap.parse_args()
    asyncio.run(seed(args.email, args.reset))
