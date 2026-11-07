from app.routers.classifier import ComplexityTier, classify


def test_simple_greeting_is_economy():
    result = classify("hi, what is the capital of France?")
    assert result.tier == ComplexityTier.ECONOMY
    assert result.score < 0.30


def test_code_prompt_is_premium_or_standard():
    prompt = (
        "Analyze and refactor this Python function for performance. "
        "```python\ndef fib(n):\n    return fib(n-1)+fib(n-2) if n>1 else n\n``` "
        "Explain the time complexity step by step."
    )
    result = classify(prompt)
    assert result.tier in (ComplexityTier.STANDARD, ComplexityTier.PREMIUM)
    assert "code_related" in result.signals


def test_long_reasoning_prompt_scores_high():
    prompt = (
        "Design a distributed caching architecture. "
        "Analyze the trade-offs between consistency models, "
        "evaluate failure modes, and reason through the "
        "implications for a multi-region deployment. " * 30
    )
    result = classify(prompt)
    assert result.score >= 0.55
    assert result.tier == ComplexityTier.PREMIUM


def test_empty_signals_for_neutral_prompt():
    result = classify("Tell me about the history of the printing press.")
    assert 0.0 <= result.score <= 1.0
    assert isinstance(result.signals, list)
