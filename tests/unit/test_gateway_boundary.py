"""Additional edge-case and boundary tests for LLMGateway and CircuitBreaker."""

import pytest

from peptalk.llm.gateway import (
    CircuitBreaker,
    FakeLLM,
    LLMGateway,
    cost_inr,
)


@pytest.fixture
def noop_sleep():
    async def _sleep(_seconds: float) -> None:
        pass

    return _sleep


# 1. Broken recorder does not break answers
@pytest.mark.asyncio
async def test_recorder_failure_does_not_break_answer(noop_sleep):
    async def broken_recorder(_row: dict) -> None:
        raise RuntimeError("Database connection lost")

    provider = FakeLLM("gemini", "gemini-3.8-flash", ["Still answers cleanly"])
    gateway = LLMGateway([provider], recorder=broken_recorder, sleep=noop_sleep)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])
    assert result.text == "Still answers cleanly"


# 2. Circuit breaker cooldown boundary check
def test_circuit_breaker_boundary_cooldown_not_expired():
    clock_time = 100.0

    def mock_clock() -> float:
        return clock_time

    cb = CircuitBreaker(threshold=2, cooldown=30.0, clock=mock_clock)
    cb.failure()
    cb.failure()
    assert cb.state == "open"
    assert cb.allow() is False

    # Just 0.1s before cooldown expires
    clock_time += 29.9
    assert cb.state == "open"
    assert cb.allow() is False

    # Exactly reaches cooldown
    clock_time += 0.1
    assert cb.state == "half-open"
    assert cb.allow() is True


# 3. Single failure does not trip threshold of 3
def test_circuit_breaker_single_failure_does_not_open():
    cb = CircuitBreaker(threshold=3, cooldown=30.0)
    cb.failure()
    assert cb.state == "closed"
    assert cb.failures == 1
    assert cb.allow() is True


# 4. Cost calculations for all 4 listed models
def test_cost_inr_all_supported_models():
    # gemini-3.8-flash: (0.75, 3.75)
    c1 = cost_inr("gemini-3.8-flash", 1_000_000, 1_000_000, 95.0)
    assert c1 == 427.5

    # gemini-3.5-flash-lite: (0.30, 2.50)
    c2 = cost_inr("gemini-3.5-flash-lite", 1_000_000, 1_000_000, 95.0)
    assert c2 == round((0.30 + 2.50) * 95.0, 6)

    # openai/gpt-oss-20b: (0.075, 0.30)
    c3 = cost_inr("openai/gpt-oss-20b", 1_000_000, 1_000_000, 95.0)
    assert c3 == round((0.075 + 0.30) * 95.0, 6)

    # openai/gpt-oss-120b: (0.15, 0.60)
    c4 = cost_inr("openai/gpt-oss-120b", 1_000_000, 1_000_000, 95.0)
    assert c4 == round((0.15 + 0.60) * 95.0, 6)
