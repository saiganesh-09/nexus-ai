"""Rule-based prompt complexity classifier.

This is a deterministic heuristic scorer — NOT a trained model. It estimates
prompt complexity from length, task type, code presence, domain keywords
and reasoning signals, then maps the score to a tier. The interface is
intentionally pluggable so a learned classifier can replace it later.

Known limitation: heuristics cannot capture semantic difficulty — a short
but subtle question may be misclassified, and verbose simple prompts may be
over-classified. Routing decisions are always recorded so accuracy can be
measured from real usage.
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
    r"```|\b(def|class|async|await|import|console\.log|function\s*\(|=>|"
    r"algorithm|debug|refactor|optimize)\b",
    re.IGNORECASE,
)

_REASONING_KEYWORDS = re.compile(
    r"\b(prove|derive|theorem|paradox|optimize|trade-?off|analyze|"
    r"evaluate|compare and contrast|root cause|architect|design a system|"
    r"step[- ]by[- ]step|reason through)\b",
    re.IGNORECASE,
)

_TASK_VERBS = re.compile(
    r"\b(explain|compare|write|create|draft|summari[sz]e|analy[sz]e|describe|"
    r"list|design|architect|debug|refactor|optimize|recommend|derive|prove|"
    r"implement|build|develop|translate|rewrite)\b",
    re.IGNORECASE,
)

_TECHNICAL_DOMAIN = re.compile(
    r"\b(api|rest|graphql|sql|select|tcp|udp|https|tls|ssl|python|javascript|"
    r"typescript|kubernetes|docker|nginx|algorithm|cryptograph\w*|distributed|"
    r"microservices?|monolith|quantum|machine learning|neural|regression|"
    r"regularization|cache|caching|saaS|auth\w*|billing|deployment|"
    r"financial|economics?|database|query|recursion|compiler|operating system)\b",
    re.IGNORECASE,
)

_WRITING_DOMAIN = re.compile(
    r"\b(email|letter|essay|article|blog|report|story|poem|cover letter|"
    r"resume|presentation|speech|linkedin post)\b",
    re.IGNORECASE,
)

_SIMPLE_KEYWORDS = re.compile(
    r"\b(hi|hello|hey|thanks|thank you|what is|who is|define|meaning of|"
    r"capital of|spell)\b",
    re.IGNORECASE,
)

_SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def classify(prompt: str) -> Classification:
    signals: list[str] = []
    score = 0.0
    length = len(prompt)

    # --- Length signals ---
    if length < 80:
        score += 0.05
        signals.append("short_prompt")
    elif length <= 400:
        score += 0.05
        signals.append("substantive_prompt")
    elif length <= 1200:
        score += 0.15
        signals.append("long_prompt")
    else:
        score += 0.25
        signals.append("very_long_prompt")

    # --- Content signals ---
    if _CODE_INDICATORS.search(prompt):
        score += 0.20
        signals.append("code_related")
    if _REASONING_KEYWORDS.search(prompt):
        score += 0.30
        signals.append("reasoning_keywords")
    if _TASK_VERBS.search(prompt):
        score += 0.20
        signals.append("task_oriented")
    if _TECHNICAL_DOMAIN.search(prompt):
        score += 0.10
        signals.append("technical_domain")
    if _WRITING_DOMAIN.search(prompt):
        score += 0.10
        signals.append("writing_task")
    if len(_SENTENCE_END.findall(prompt)) >= 2:
        score += 0.05
        signals.append("multi_sentence")
    if prompt.count("?") >= 3:
        score += 0.10
        signals.append("multi_part_question")
    if _SIMPLE_KEYWORDS.search(prompt) and length < 200:
        score -= 0.15
        signals.append("simple_lookup")

    score = max(0.0, min(1.0, score))

    if score >= 0.55:
        tier = ComplexityTier.PREMIUM
    elif score >= 0.30:
        tier = ComplexityTier.STANDARD
    else:
        tier = ComplexityTier.ECONOMY

    return Classification(score=round(score, 3), tier=tier, signals=signals)
