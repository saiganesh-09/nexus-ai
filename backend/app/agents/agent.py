"""Tool-using agent loop.

Protocol: the LLM replies either {"tool": name, "args": {...}} to call a
tool, or {"answer": "..."} to finish. Provider-agnostic — works with any
chat completion. Execution is bounded by max_steps and every step is
logged for evaluation.
"""

import json
import re
import time
from dataclasses import dataclass, field

from app.agents.tools import ToolRegistry, registry as default_registry
from app.providers.base import ChatMessage
from app.providers.registry import get_provider

SYSTEM_PROMPT = """You are NEXUS Agent, an assistant with access to tools.
Available tools:
{tools}

To use a tool, reply with ONLY a JSON object: {{"tool": "<name>", "args": {{...}}}}
When you have the final answer, reply with ONLY: {{"answer": "<your answer>"}}
Never invent tool results — always call the tool first when needed."""

MAX_STEPS = 5


@dataclass
class AgentStep:
    step: int
    action: str  # "tool_call" | "final_answer" | "error"
    tool: str | None = None
    args: dict | None = None
    result: object | None = None
    ok: bool | None = None
    error: str | None = None


@dataclass
class AgentRun:
    prompt: str
    answer: str | None
    steps: list[AgentStep] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tool_errors: int = 0
    completed: bool = False
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    provider_error: str | None = None


def _parse_action(text: str) -> dict | None:
    """Extract the first JSON object from model output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


async def run_agent(
    prompt: str,
    provider_name: str,
    model_id: str,
    *,
    tools: ToolRegistry | None = None,
    max_steps: int = MAX_STEPS,
    temperature: float = 0.0,
) -> AgentRun:
    tools = tools or default_registry
    provider = get_provider(provider_name)
    if provider is None or not provider.is_configured():
        return AgentRun(prompt=prompt, answer=None, provider_error="provider not configured")

    run = AgentRun(prompt=prompt, answer=None, model=model_id)
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT.format(tools=tools.describe())),
        ChatMessage(role="user", content=prompt),
    ]
    start = time.perf_counter()

    for step in range(1, max_steps + 1):
        try:
            resp = await provider.complete(messages, model_id, temperature=temperature)
        except Exception as exc:
            run.provider_error = str(exc)[:500]
            break

        run.input_tokens = (run.input_tokens or 0) + (resp.input_tokens or 0)
        run.output_tokens = (run.output_tokens or 0) + (resp.output_tokens or 0)

        action = _parse_action(resp.content)
        if action is None:
            # Model didn't follow protocol — treat raw text as the answer.
            run.steps.append(AgentStep(step=step, action="final_answer", result=resp.content[:200]))
            run.answer = resp.content.strip()
            run.completed = True
            break

        if "answer" in action:
            run.steps.append(AgentStep(step=step, action="final_answer", result=str(action["answer"])[:200]))
            run.answer = str(action["answer"])
            run.completed = True
            break

        tool_name = action.get("tool")
        tool_args = action.get("args") or {}
        result = tools.execute(str(tool_name), tool_args if isinstance(tool_args, dict) else {})
        run.steps.append(
            AgentStep(
                step=step, action="tool_call", tool=str(tool_name),
                args=tool_args, result=result.output, ok=result.ok, error=result.error,
            )
        )
        run.tools_used.append(str(tool_name))
        if not result.ok:
            run.tool_errors += 1
        messages.append(ChatMessage(role="assistant", content=resp.content))
        messages.append(
            ChatMessage(
                role="user",
                content=f"Tool result: {json.dumps(result.output if result.ok else {'error': result.error})}",
            )
        )
    else:
        run.steps.append(AgentStep(step=max_steps, action="error", error="max_steps exceeded"))

    run.latency_ms = int((time.perf_counter() - start) * 1000)
    return run
