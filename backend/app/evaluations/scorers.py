"""Deterministic graders — no LLM judge anywhere in this module.

Every grader inspects the agent's final answer (and optionally its tool
trace) with string/regex checks. Scores are binary pass/fail plus a
partial-credit heuristic for multi-part answers.
"""

import re
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def grade(grader: dict, answer: str | None, run: Any = None) -> tuple[bool, float, dict]:
    """Returns (passed, score 0-1, details)."""
    details: dict[str, Any] = {"grader": grader.get("type")}
    if answer is None:
        return False, 0.0, {**details, "reason": "no answer produced"}

    gtype = grader.get("type")
    expected = grader.get("expected")
    norm = _norm(answer)

    if gtype == "contains":
        ok = _norm(str(expected)) in norm
        return ok, 1.0 if ok else 0.0, {**details, "matched": ok}

    if gtype == "contains_all":
        expected_list = expected if isinstance(expected, list) else [expected]
        hits = sum(1 for e in expected_list if _norm(str(e)) in norm)
        score = hits / len(expected_list)
        return score == 1.0, score, {**details, "hits": hits, "total": len(expected_list)}

    if gtype == "contains_any":
        expected_list = expected if isinstance(expected, list) else [expected]
        ok = any(_norm(str(e)) in norm for e in expected_list)
        return ok, 1.0 if ok else 0.0, {**details, "matched": ok}

    if gtype == "exact":
        ok = norm.strip() == _norm(str(expected)).strip()
        return ok, 1.0 if ok else 0.0, {**details, "matched": ok}

    if gtype == "regex":
        ok = re.search(str(expected), answer or "") is not None
        return ok, 1.0 if ok else 0.0, {**details, "matched": ok}

    return False, 0.0, {**details, "reason": f"unknown grader type '{gtype}'"}


def tool_metrics(run: Any, allowed_tools: list[str]) -> dict:
    """Tool-selection/execution metrics derived from the agent trace."""
    used = set(run.tools_used) if run else set()
    allowed = set(allowed_tools)
    steps = run.steps if run else []
    tool_steps = [s for s in steps if s.action == "tool_call"]
    successful = [s for s in tool_steps if s.ok]
    return {
        "tools_used": sorted(used),
        "allowed_tools": sorted(allowed),
        "tool_selection_ok": used.issubset(allowed) if used else None,
        "tool_calls": len(tool_steps),
        "tool_successes": len(successful),
        "tool_errors": run.tool_errors if run else 0,
        "execution_steps": len(steps),
    }
