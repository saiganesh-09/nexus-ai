"""Controlled agent tools — deterministic, side-effect free, validated."""

import ast
import operator
import re
from dataclasses import dataclass, field
from typing import Any


class ToolError(Exception):
    pass


@dataclass
class ToolResult:
    ok: bool
    output: Any
    error: str | None = None


@dataclass
class Tool:
    name: str = ""
    description: str = ""
    parameters: dict[str, str] = field(default_factory=dict)  # param -> description

    def validate(self, args: dict) -> None:
        for key in self.parameters:
            if key not in args:
                raise ToolError(f"missing required parameter '{key}'")
        extra = set(args) - set(self.parameters)
        if extra:
            raise ToolError(f"unexpected parameters: {sorted(extra)}")

    def run(self, args: dict) -> ToolResult:
        raise NotImplementedError


# ---------------- Calculator ----------------

_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}
_MAX_ABS = 1e15


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError("only numeric literals allowed")
        v = float(node.value)
        if abs(v) > _MAX_ABS:
            raise ToolError("number out of range")
        return v
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ToolError(f"disallowed expression element: {type(node).__name__}")


@dataclass
class CalculatorTool(Tool):
    name: str = "calculator"
    description: str = "Evaluate a mathematical expression (+ - * / // % ** parentheses)."
    parameters: dict = field(default_factory=lambda: {"expression": "arithmetic expression string"})

    def run(self, args: dict) -> ToolResult:
        self.validate(args)
        expr = str(args["expression"])[:500]
        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree)
        except ToolError as exc:
            return ToolResult(ok=False, output=None, error=str(exc))
        except Exception as exc:
            return ToolResult(ok=False, output=None, error=f"invalid expression: {exc}")
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return ToolResult(ok=True, output=result)


# ---------------- Knowledge lookup ----------------

_KNOWLEDGE_BASE = {
    "capital of france": "Paris",
    "capital of japan": "Tokyo",
    "capital of germany": "Berlin",
    "capital of australia": "Canberra",
    "capital of canada": "Ottawa",
    "capital of brazil": "Brasília",
    "capital of egypt": "Cairo",
    "capital of india": "New Delhi",
    "capital of italy": "Rome",
    "capital of spain": "Madrid",
    "capital of china": "Beijing",
    "capital of russia": "Moscow",
    "capital of south korea": "Seoul",
    "capital of mexico": "Mexico City",
    "capital of argentina": "Buenos Aires",
    "capital of turkey": "Ankara",
    "speed of light": "299,792,458 meters per second",
    "boiling point of water": "100 degrees Celsius at standard atmospheric pressure",
    "chemical symbol for gold": "Au",
    "chemical symbol for iron": "Fe",
    "chemical symbol for sodium": "Na",
    "largest planet": "Jupiter",
    "smallest planet": "Mercury",
    "author of romeo and juliet": "William Shakespeare",
    "author of the bible": "Multiple authors",
    "inventor of the telephone": "Alexander Graham Bell",
    "year moon landing": "1969",
    "number of continents": "7",
    "largest ocean": "Pacific Ocean",
    "hardest natural substance": "Diamond",
    "currency of japan": "Yen",
    "currency of uk": "Pound sterling",
    "currency of india": "Rupee",
    "currency of canada": "Canadian dollar",
    "planet closest to sun": "Mercury",
    "tallest mountain": "Mount Everest",
    "largest mammal": "Blue whale",
    "longest river": "Nile River (commonly cited; Amazon is longer by some measures)",
}


@dataclass
class KnowledgeTool(Tool):
    name: str = "knowledge_lookup"
    description: str = "Look up a factual question in the built-in knowledge base (capitals, science facts, history)."
    parameters: dict = field(default_factory=lambda: {"query": "natural language question or topic"})

    def run(self, args: dict) -> ToolResult:
        self.validate(args)
        q = re.sub(r"\s+", " ", str(args["query"]).lower()).strip("? .!")
        # Exact then substring matching.
        for key, answer in _KNOWLEDGE_BASE.items():
            if q == key or key in q or q in key:
                return ToolResult(ok=True, output=answer)
        return ToolResult(
            ok=False, output=None,
            error=f"no knowledge base entry for '{args['query']}'",
        )


# ---------------- Code analysis ----------------

@dataclass
class CodeAnalysisTool(Tool):
    name: str = "code_analysis"
    description: str = "Analyze Python source code: count lines/functions/classes, detect TODOs/prints, estimate complexity."
    parameters: dict = field(default_factory=lambda: {"code": "Python source code string"})

    def run(self, args: dict) -> ToolResult:
        self.validate(args)
        code = str(args["code"])[:50000]
        if len(code) > 50000:
            return ToolResult(ok=False, output=None, error="code exceeds 50KB limit")
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return ToolResult(ok=False, output=None, error=f"syntax error: {exc}")

        lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
        functions = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
        classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        branches = sum(
            isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp, ast.IfExp))
            for n in ast.walk(tree)
        )
        todos = len(re.findall(r"#\s*TODO|#\s*FIXME|#\s*HACK", code))
        prints = len(re.findall(r"\bprint\s*\(", code))
        complexity = 1 + branches

        return ToolResult(ok=True, output={
            "lines_of_code": len(lines),
            "functions": functions,
            "classes": classes,
            "estimated_cyclomatic_complexity": complexity,
            "todo_comments": todos,
            "print_calls": prints,
        })


# ---------------- Registry ----------------

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        for tool in (CalculatorTool(), KnowledgeTool(), CodeAnalysisTool()):
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> str:
        return "\n".join(
            f"- {t.name}({', '.join(t.parameters)}): {t.description}"
            for t in self._tools.values()
        )

    def execute(self, name: str, args: dict) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(ok=False, output=None, error=f"unknown tool '{name}'")
        try:
            if not isinstance(args, dict):
                raise ToolError("tool arguments must be an object")
            return tool.run(args)
        except ToolError as exc:
            return ToolResult(ok=False, output=None, error=str(exc))
        except Exception as exc:
            return ToolResult(ok=False, output=None, error=f"tool crashed: {exc}")


registry = ToolRegistry()
