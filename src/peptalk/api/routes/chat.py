"""POST /v1/chat (streaming), GET /v1/usage, and GET /v1/llm/status."""

import json
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from peptalk.api.deps import GatewayDep, UsageDep
from peptalk.llm.gateway import LLMResult, LLMUnavailable

router = APIRouter(tags=["chat"])
PROMPT_VERSION = "chat_system_v1"  # the file prompts/chat_system_v1.md


def load_prompt(directory: Path, name: str = PROMPT_VERSION) -> str:
    """Read a prompt file. A missing file stops the app at start-up: fail fast."""
    return (directory / f"{name}.md").read_text(encoding="utf-8").strip()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    stream: bool = True
    history: list[ChatMessage] = Field(default_factory=list, max_length=6)


def sse(data: dict, event: str = "") -> str:
    """One server-sent event: an optional name, a JSON payload, and a blank line."""
    head = f"event: {event}\n" if event else ""
    return f"{head}data: {json.dumps(data, ensure_ascii=False)}\n\n"


def summary(result: LLMResult) -> dict:
    return {k: v for k, v in asdict(result).items() if k != "text"}


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, gateway: GatewayDep):
    messages: list[dict[str, str]] = [
        {"role": "system", "content": request.app.state.system_prompt}
    ]
    for msg in body.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.message})

    try:
        if not body.stream:
            result = await gateway.generate(messages, prompt_version=PROMPT_VERSION)
            return {"answer": result.text, **summary(result)}
        stream = gateway.stream(messages, prompt_version=PROMPT_VERSION)
        first = await anext(stream)  # wait for the first piece BEFORE sending status 200
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"No model could answer: {exc}") from exc

    async def events() -> AsyncIterator[str]:
        item: str | LLMResult = first
        try:
            while True:
                if isinstance(item, LLMResult):
                    yield sse(summary(item), event="done")
                    return
                yield sse({"delta": item})
                item = await anext(stream)
        except LLMUnavailable as exc:
            # the status line is long gone: say it in the stream
            yield sse({"detail": str(exc)}, event="error")

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)


@router.get("/usage")
async def usage(repo: UsageDep, days: Annotated[int, Query(ge=1, le=90)] = 7) -> dict:
    """Tokens, rupees per day, and latency percentiles from the llm_calls table."""
    rows = await repo.by_day(days)
    latency = await repo.latency_percentiles(days)
    total = round(sum(row["cost_inr"] for row in rows), 4)
    return {
        "days": rows,
        "total_cost_inr": total,
        "calls": sum(row["calls"] for row in rows),
        "latency": latency,
    }


@router.get("/usage/percentiles")
async def usage_percentiles(repo: UsageDep, days: Annotated[int, Query(ge=1, le=90)] = 7) -> dict:
    """Latency distribution (p50, p90, p95, p99) against the Day 1 non-functional target."""
    return await repo.latency_percentiles(days)


@router.get("/llm/status")
async def llm_status(gateway: GatewayDep) -> dict:
    """Live health, failure counts, and circuit breaker states for all LLM providers."""
    providers_status: list[dict] = []
    any_healthy = False
    all_healthy = True

    for provider in gateway.providers:
        breaker = gateway.breakers.get(provider.name)
        state = breaker.state if breaker else "unknown"
        failures = breaker.failures if breaker else 0
        cooldown = breaker.cooldown if breaker else 0.0
        is_healthy = state != "open"

        if is_healthy:
            any_healthy = True
        else:
            all_healthy = False

        providers_status.append(
            {
                "name": provider.name,
                "model": provider.model,
                "state": state,
                "healthy": is_healthy,
                "failures": failures,
                "cooldown_seconds": cooldown,
            }
        )

    overall = "healthy" if all_healthy else ("degraded" if any_healthy else "unavailable")
    return {
        "status": overall,
        "providers_count": len(providers_status),
        "providers": providers_status,
    }
