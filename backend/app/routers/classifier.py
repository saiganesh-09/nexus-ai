"""Rule-based prompt complexity classifier.

This is a deterministic heuristic scorer — NOT a trained model. It estimates
prompt complexity from length, task type, code presence and keywords, then
maps the score to a tier. The interface is intentionally pluggable so a
learned classifier can replace it later.
"""

import re
from dataclasses import dataclass
from enum import Enum


class ComplexityTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class Classification:
    score: float  # 0.0 – 1.0
    tier: ComplexityTier
    signals: list[str]


_CODE_INDICATORS = re.compile(
    r"```|\b(def|class|function|import|async|await|SELECT|console\.log|"
    r"function\s*\(|=>|\{\s*\}|algorithm|debug|refactor|optimize)\b",
    re.IGNORECASE,
)

_REASONING_KEYWORDS = re.compile(
    r"\b(prove|derive|theorem|paradox|optimize|trade-?off|analyze|"
    r"evaluate|compare and contrast|root cause|architect|design a system|"
    r"step[- ]by[- ]step|reason through)\b",
    re.IGNORECASE,
)

_SIMPLE_KEYWORDS = re.compile(
    r"\b(hi|hello|hey|thanks|thank you|what is|who is|when|where|yes|no|"
    r"define|meaning of|capital of|spell)\b",
    re.IGNORECASE,
)


def classify(prompt: str) -> Classification:
    signals: list[str] = []
    score = 0.0

    length = len(prompt)
    if length < 80:
        score += 0.05
        signals.append("short_prompt")
    elif length > 1200:
        score += 0.25
        signals.append("very_long_prompt")
    elif length > 400:
        score += 0.15
        signals.append("long_prompt")

    if _CODE_INDICATORS.search(prompt):
        score += 0.30
        signals.append("code_related")
    if _REASONING_KEYWORDS.search(prompt):
        score += 0.30
        signals.append("reasoning_keywords")
    if _SIMPLE_KEYWORDS.search(prompt) and length < 200:
        score -= 0.15
        signals.append("simple_lookup")
    if prompt.count("?") >= 3:
        score += 0.10
        signals.append("multi_part_question")

    score = max(0.0, min(1.0, score))

    if score >= 0.55:
        tier = ComplexityTier.PREMIUM
    elif score >= 0.30:
        tier = ComplexityTier.STANDARD
    else:
        tier = ComplexityTier.ECONOMY

    return Classification(score=round(score, 3), tier=tier, signals=signals)
