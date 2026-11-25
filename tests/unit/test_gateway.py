"""Unit tests for LLMGateway, CircuitBreaker, FakeLLM, and cost calculation.

All 19 tests run in-memory with FakeLLM: no network, no API key, no external calls.
"""

import pytest

from peptalk.config import Settings
from peptalk.llm.gateway import (
    CircuitBreaker,
    FakeLLM,
    LLMError,
    LLMGateway,
    LLMResult,
    LLMUnavailable,
    build_gateway,
    cost_inr,
    estimate_tokens,
)


@pytest.fixture
def noop_sleep():
    async def _sleep(_seconds: float) -> None:
        pass

    return _sleep


# 1. Happy path generate
@pytest.mark.asyncio
async def test_generate_happy_path(noop_sleep):
    provider = FakeLLM("gemini", "gemini-3.8-flash", ["Hello world!"])
    gateway = LLMGateway([provider], sleep=noop_sleep)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])

    assert isinstance(result, LLMResult)
    assert result.text == "Hello world!"
    assert result.provider == "gemini"
    assert result.model == "gemini-3.8-flash"
    assert result.fallback_used is False
    assert result.attempts == 1
    assert result.tokens_in == 12
    assert result.tokens_out == 2
    assert result.cost_inr > 0


# 2. Recorder hook
@pytest.mark.asyncio
async def test_generate_records_call(noop_sleep):
    recorded = []

    async def recorder(row: dict) -> None:
        recorded.append(row)

    provider = FakeLLM("gemini", "gemini-3.8-flash", ["Success"])
    gateway = LLMGateway([provider], recorder=recorder, sleep=noop_sleep)

    await gateway.generate([{"role": "user", "content": "Ping"}], purpose="test")

    assert len(recorded) == 1
    assert recorded[0]["status"] == "ok"
    assert recorded[0]["provider"] == "gemini"
    assert recorded[0]["purpose"] == "test"
    assert recorded[0]["tokens_in"] == 12


# 3. Retry on retryable error
@pytest.mark.asyncio
async def test_generate_retry_on_retryable_error(noop_sleep):
    script = [LLMError("429 Rate limit", retryable=True), "Recovered after retry"]
    provider = FakeLLM("gemini", "gemini-3.8-flash", script)
    gateway = LLMGateway([provider], sleep=noop_sleep)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])

    assert result.text == "Recovered after retry"
    assert result.attempts == 2
    assert provider.calls == 2


# 4. No retry on non-retryable error (falls back directly)
@pytest.mark.asyncio
async def test_generate_no_retry_on_non_retryable_error(noop_sleep):
    primary = FakeLLM("gemini", "gemini-3.8-flash", [LLMError("400 Bad request", retryable=False)])
    fallback = FakeLLM("groq", "openai/gpt-oss-20b", ["Fallback answer"])
    gateway = LLMGateway([primary, fallback], sleep=noop_sleep)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])

    assert result.text == "Fallback answer"
    assert result.provider == "groq"
    assert result.fallback_used is True
    assert primary.calls == 1


# 5. Fallback when primary retries are exhausted
@pytest.mark.asyncio
async def test_generate_fallback_when_primary_exhausted(noop_sleep):
    primary = FakeLLM(
        "gemini",
        "gemini-3.8-flash",
        [
            LLMError("500 Server error", retryable=True),
            LLMError("500 Server error", retryable=True),
        ],
    )
    fallback = FakeLLM("groq", "openai/gpt-oss-20b", ["Groq saved the day"])
    gateway = LLMGateway([primary, fallback], sleep=noop_sleep)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])

    assert result.text == "Groq saved the day"
    assert result.provider == "groq"
    assert result.fallback_used is True
    assert primary.calls == 2


# 6. All providers fail raises LLMUnavailable
@pytest.mark.asyncio
async def test_generate_all_providers_fail_raises_llm_unavailable(noop_sleep):
    primary = FakeLLM("gemini", "gemini-3.8-flash", [LLMError("Dead", retryable=False)])
    fallback = FakeLLM("groq", "openai/gpt-oss-20b", [LLMError("Also dead", retryable=False)])
    gateway = LLMGateway([primary, fallback], sleep=noop_sleep)

    with pytest.raises(LLMUnavailable) as exc:
        await gateway.generate([{"role": "user", "content": "Hi"}])

    assert "Dead" in str(exc.value)
    assert "Also dead" in str(exc.value)


# 7. Circuit breaker opens after threshold failures
@pytest.mark.asyncio
async def test_generate_circuit_breaker_opens_after_threshold_failures(noop_sleep):
    simulated_time = 100.0

    def mock_clock() -> float:
        return simulated_time

    provider = FakeLLM(
        "gemini",
        "gemini-3.8-flash",
        [
            LLMError("err1", retryable=False),
            LLMError("err2", retryable=False),
            LLMError("err3", retryable=False),
            "Never reached",
        ],
    )
    gateway = LLMGateway(
        [provider],
        breaker_threshold=3,
        breaker_cooldown=30.0,
        clock=mock_clock,
        sleep=noop_sleep,
    )

    for _ in range(3):
        with pytest.raises(LLMUnavailable):
            await gateway.generate([{"role": "user", "content": "Hi"}])

    assert gateway.breakers["gemini"].state == "open"

    with pytest.raises(LLMUnavailable) as exc:
        await gateway.generate([{"role": "user", "content": "Hi"}])
    assert "circuit open" in str(exc.value)
    assert provider.calls == 3


# 8. Circuit breaker half-open after cooldown
@pytest.mark.asyncio
async def test_generate_circuit_breaker_half_open_after_cooldown(noop_sleep):
    simulated_time = 100.0

    def mock_clock() -> float:
        return simulated_time

    breaker = CircuitBreaker(threshold=2, cooldown=30.0, clock=mock_clock)
    breaker.failure()
    breaker.failure()
    assert breaker.state == "open"
    assert breaker.allow() is False

    simulated_time += 31.0
    assert breaker.state == "half-open"
    assert breaker.allow() is True


# 9. Circuit breaker resets on success
@pytest.mark.asyncio
async def test_generate_circuit_breaker_resets_on_success(noop_sleep):
    breaker = CircuitBreaker(threshold=3, cooldown=30.0)
    breaker.failure()
    breaker.failure()
    assert breaker.failures == 2

    breaker.success()
    assert breaker.failures == 0
    assert breaker.state == "closed"


# 10. Streaming happy path
@pytest.mark.asyncio
async def test_stream_happy_path():
    provider = FakeLLM("gemini", "gemini-3.8-flash", ["one two three"])
    gateway = LLMGateway([provider])

    chunks: list[str] = []
    final_result: LLMResult | None = None

    async for item in gateway.stream([{"role": "user", "content": "Count"}]):
        if isinstance(item, LLMResult):
            final_result = item
        else:
            chunks.append(item)

    assert "".join(chunks) == "one two three "
    assert final_result is not None
    assert final_result.provider == "gemini"
    assert final_result.tokens_out == 3
    assert final_result.fallback_used is False


# 11. Stream records call
@pytest.mark.asyncio
async def test_stream_records_call():
    recorded = []

    async def recorder(row: dict) -> None:
        recorded.append(row)

    provider = FakeLLM("gemini", "gemini-3.8-flash", ["streaming answer"])
    gateway = LLMGateway([provider], recorder=recorder)

    async for _ in gateway.stream([{"role": "user", "content": "Stream"}]):
        pass

    assert len(recorded) == 1
    assert recorded[0]["status"] == "ok"
    assert recorded[0]["provider"] == "gemini"


# 12. Stream fallback before first piece
@pytest.mark.asyncio
async def test_stream_fallback_before_first_piece():
    primary = FakeLLM("gemini", "gemini-3.8-flash", [LLMError("Stream refused", retryable=False)])
    fallback = FakeLLM("groq", "openai/gpt-oss-20b", ["Fallback stream"])
    gateway = LLMGateway([primary, fallback])

    chunks = []
    final = None
    async for item in gateway.stream([{"role": "user", "content": "Stream"}], prompt_version="v1"):
        if isinstance(item, LLMResult):
            final = item
        else:
            chunks.append(item)

    assert "".join(chunks) == "Fallback stream "
    assert final is not None
    assert final.provider == "groq"
    assert final.fallback_used is True


# 13. Stream mid-answer failure does not switch models
@pytest.mark.asyncio
async def test_stream_mid_answer_failure_does_not_fallback():
    partial_error = ("partial", LLMError("Connection dropped mid-stream", retryable=False))
    primary = FakeLLM("gemini", "gemini-3.8-flash", [partial_error])
    fallback = FakeLLM("groq", "openai/gpt-oss-20b", ["Should not be called"])
    gateway = LLMGateway([primary, fallback])

    chunks = []
    with pytest.raises(LLMUnavailable) as exc:
        async for item in gateway.stream([{"role": "user", "content": "Stream"}]):
            if isinstance(item, str):
                chunks.append(item)

    assert len(chunks) > 0  # user already saw partial answer
    assert "failed mid-answer" in str(exc.value)
    assert fallback.calls == 0  # Fallback was NOT contacted to avoid model collision


# 14. Circuit breaker direct methods
def test_circuit_breaker_direct_methods():
    cb = CircuitBreaker(threshold=1, cooldown=10.0)
    assert cb.state == "closed"
    assert cb.allow() is True

    cb.failure()
    assert cb.state == "open"
    assert cb.allow() is False

    cb.success()
    assert cb.state == "closed"
    assert cb.allow() is True


# 15. Cost INR calculation
def test_cost_inr_calculation():
    # gemini-3.8-flash: (0.75, 3.75) per 1M tokens. usd_inr = 95.0
    # 1,000,000 in, 1,000,000 out: (0.75 + 3.75) * 95 = 4.5 * 95 = 427.5
    cost = cost_inr("gemini-3.8-flash", 1_000_000, 1_000_000, 95.0)
    assert cost == 427.5


# 16. Cost INR unknown model returns 0
def test_cost_inr_unknown_model():
    assert cost_inr("unknown-model", 1000, 1000, 95.0) == 0.0


# 17. Token estimation
def test_estimate_tokens():
    assert estimate_tokens("") == 1
    assert estimate_tokens("hello") == 1
    assert estimate_tokens("a" * 40) == 10


# 18. build_gateway filters missing keys
def test_build_gateway_filters_missing_keys():
    settings = Settings(
        app_env="ci",
        gemini_api_key="",
        groq_api_key="groq-test-key",  # pragma: allowlist secret
        _env_file=None,
    )
    gw = build_gateway(settings)
    assert len(gw.providers) == 1
    assert gw.providers[0].name == "groq"

    empty_settings = Settings(
        app_env="ci",
        gemini_api_key="",
        groq_api_key="",
        _env_file=None,
    )
    empty_gw = build_gateway(empty_settings)
    assert len(empty_gw.providers) == 0


# 19. Broken recorder does not break answers
@pytest.mark.asyncio
async def test_recorder_failure_does_not_break_answer(noop_sleep):
    async def broken_recorder(_row: dict) -> None:
        raise RuntimeError("Database connection lost")

    provider = FakeLLM("gemini", "gemini-3.8-flash", ["Still answers cleanly"])
    gateway = LLMGateway([provider], recorder=broken_recorder, sleep=noop_sleep)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])
    assert result.text == "Still answers cleanly"


# 20. Circuit breaker cooldown boundary check
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


# 21. Single failure does not trip threshold of 3
def test_circuit_breaker_single_failure_does_not_open():
    cb = CircuitBreaker(threshold=3, cooldown=30.0)
    cb.failure()
    assert cb.state == "closed"
    assert cb.failures == 1
    assert cb.allow() is True


# 22. Cost calculations for all 4 listed models
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


# 23. Stream handles empty chunks gracefully
@pytest.mark.asyncio
async def test_stream_empty_chunk_handled():
    provider = FakeLLM("gemini", "gemini-3.8-flash", [""])
    gateway = LLMGateway([provider])

    chunks = []
    async for item in gateway.stream([{"role": "user", "content": "Hi"}]):
        if isinstance(item, str):
            chunks.append(item)

    assert chunks == []


# 24. Generate passes custom temperature option
@pytest.mark.asyncio
async def test_generate_passes_custom_options(noop_sleep):
    provider = FakeLLM("gemini", "gemini-3.8-flash", ["Cold answer"])
    gateway = LLMGateway([provider], sleep=noop_sleep)

    result = await gateway.generate(
        [{"role": "user", "content": "Hi"}],
        temperature=0.0,
    )
    assert result.text == "Cold answer"
    assert result.attempts == 1


# 25. Exponential backoff never exceeds MAX_WAIT
@pytest.mark.asyncio
async def test_exponential_backoff_max_wait():
    from peptalk.llm.gateway import MAX_WAIT

    waited = []

    async def mock_sleep(s: float) -> None:
        waited.append(s)

    script = [
        LLMError("429 Rate limit", retryable=True, retry_after=500.0),
        "Answer after cap",
    ]
    provider = FakeLLM("gemini", "gemini-3.8-flash", script)
    gateway = LLMGateway([provider], sleep=mock_sleep, max_attempts=2)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])
    assert result.text == "Answer after cap"
    assert len(waited) == 1
    assert waited[0] <= MAX_WAIT  # Capped at 20.0s
