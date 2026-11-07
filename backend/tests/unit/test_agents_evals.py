"""Agent tools, agent loop and evaluation tests."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.agents.tools import CalculatorTool, CodeAnalysisTool, KnowledgeTool, ToolRegistry
from app.evaluations.scorers import grade, tool_metrics
from app.evaluations.dataset import DATASET
from tests.conftest import auth_headers, register_user


# ---------- Tools ----------

def test_calculator_basic():
    r = CalculatorTool().run({"expression": "2 + 3 * 4"})
    assert r.ok and r.output == 14


def test_calculator_rejects_unsafe():
    r = CalculatorTool().run({"expression": "__import__('os').system('ls')"})
    assert not r.ok


def test_calculator_validates_params():
    from app.agents.tools import registry
    r = registry.execute("calculator", {"wrong": 1})
    assert not r.ok and "missing" in (r.error or "")


def test_knowledge_lookup():
    r = KnowledgeTool().run({"query": "capital of France?"})
    assert r.ok and "Paris" in str(r.output)


def test_code_analysis():
    code = "def f():\n    if True:\n        return 1\n    return 2\n"
    r = CodeAnalysisTool().run({"code": code})
    assert r.ok
    assert r.output["functions"] == 1
    assert r.output["estimated_cyclomatic_complexity"] >= 2


def test_code_analysis_syntax_error():
    r = CodeAnalysisTool().run({"code": "def broken(:"})
    assert not r.ok


# ---------- Scorers ----------

def test_grade_contains():
    ok, score, _ = grade({"type": "contains", "expected": "Paris"}, "The answer is Paris.")
    assert ok and score == 1.0


def test_grade_contains_all_partial():
    ok, score, _ = grade({"type": "contains_all", "expected": ["Paris", "144"]}, "Paris only")
    assert not ok and score == 0.5


def test_grade_no_answer():
    ok, score, _ = grade({"type": "contains", "expected": "x"}, None)
    assert not ok and score == 0.0


def test_dataset_integrity():
    ids = [t["id"] for t in DATASET]
    assert len(ids) == len(set(ids)) == 25
    for t in DATASET:
        assert t["allowed_tools"] and t["grader"] and t["category"]


# ---------- Agent loop (mock provider) ----------

class FakeProvider:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def is_configured(self):
        return True

    async def complete(self, messages, model, max_tokens=None, temperature=None):
        from app.providers.base import ProviderResponse
        self.calls += 1
        text = self.replies.pop(0) if self.replies else '{"answer": "done"}'
        return ProviderResponse(content=text, model=model, provider="fake",
                                input_tokens=10, output_tokens=5)


@pytest.mark.asyncio
async def test_agent_tool_then_answer(monkeypatch):
    from app.agents import agent as agent_mod
    fake = FakeProvider([
        '{"tool": "calculator", "args": {"expression": "6*7"}}',
        '{"answer": "The result is 42."}',
    ])
    monkeypatch.setattr(agent_mod, "get_provider", lambda name: fake)
    run = await agent_mod.run_agent("what is 6*7?", "fake", "fake-model")
    assert run.completed and run.answer == "The result is 42."
    assert run.tools_used == ["calculator"]
    assert run.steps[0].ok is True and run.steps[0].result == 42


@pytest.mark.asyncio
async def test_agent_unconfigured_provider():
    from app.agents import agent as agent_mod
    run = await agent_mod.run_agent("hi", "nonexistent", "m")
    assert run.answer is None and run.provider_error


@pytest.mark.asyncio
async def test_agent_max_steps(monkeypatch):
    from app.agents import agent as agent_mod
    fake = FakeProvider(['{"tool": "calculator", "args": {"expression": "1+1"}}'] * 10)
    monkeypatch.setattr(agent_mod, "get_provider", lambda name: fake)
    run = await agent_mod.run_agent("loop", "fake", "m", max_steps=2)
    assert not run.completed


# ---------- Evaluation API ----------

@pytest.fixture()
def headers(client: TestClient):
    email = f"eval-{uuid.uuid4().hex[:8]}@example.com"
    register_user(client, email)
    return auth_headers(client, email)


def test_dataset_endpoint(client: TestClient, headers):
    res = client.get("/api/v1/evaluations/dataset", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["task_count"] == 25 and len(body["tasks"]) == 25


def test_evaluations_require_auth(client: TestClient):
    assert client.get("/api/v1/evaluations/runs").status_code == 401
    assert client.post("/api/v1/evaluations/runs", json={}).status_code == 401


def test_run_with_unconfigured_provider_fails_gracefully(client: TestClient, headers):
    # Provider 'nonexistent' isn't configured → every task records a
    # provider_error and fails; run still completes and persists.
    res = client.post("/api/v1/evaluations/runs", headers=headers, json={
        "provider": "nonexistent", "model": "x", "task_ids": ["calc-01"],
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["summary"]["total_tasks"] == 1
    assert body["summary"]["passed_tasks"] == 0


def test_get_run_detail(client: TestClient, headers):
    run = client.post("/api/v1/evaluations/runs", headers=headers, json={
        "provider": "nonexistent", "model": "x", "task_ids": ["know-01"],
    }).json()
    res = client.get(f"/api/v1/evaluations/runs/{run['id']}", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert len(detail["results"]) == 1
    assert detail["results"][0]["details"]["category"] == "knowledge"


def test_other_user_cannot_read_run(client: TestClient):
    h1 = auth_headers(client, f"e1-{uuid.uuid4().hex[:6]}@x.com") if False else None
    # register two users explicitly
    e1, e2 = f"ea-{uuid.uuid4().hex[:6]}@x.com", f"eb-{uuid.uuid4().hex[:6]}@x.com"
    register_user(client, e1)
    register_user(client, e2)
    h1 = auth_headers(client, e1)
    h2 = auth_headers(client, e2)
    run = client.post("/api/v1/evaluations/runs", headers=h1, json={
        "provider": "nonexistent", "model": "x", "task_ids": ["calc-02"],
    }).json()
    assert client.get(f"/api/v1/evaluations/runs/{run['id']}", headers=h2).status_code == 404
