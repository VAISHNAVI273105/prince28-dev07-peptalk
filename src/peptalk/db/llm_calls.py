"""Database recorder and repository for LLM call logging and usage tracking."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Date, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.db.models import LlmCall
from peptalk.db.session import session_scope

logger = logging.getLogger("peptalk.llm.calls")


async def record_call(row: dict[str, Any]) -> None:
    """Record one LLM call execution to the llm_calls table in Postgres."""
    try:
        async with session_scope() as session:
            call = LlmCall(
                request_id=str(row.get("request_id") or ""),
                provider=str(row.get("provider", "unknown")),
                model=str(row.get("model", "unknown")),
                purpose=str(row.get("purpose", "chat")),
                prompt_version=str(row.get("prompt_version", "")),
                status=str(row.get("status", "ok")),
                error=str(row.get("error", "")),
                tokens_in=int(row.get("tokens_in", 0)),
                tokens_out=int(row.get("tokens_out", 0)),
                latency_ms=int(row.get("latency_ms", 0)),
                cost_inr=float(row.get("cost_inr", 0.0)),
                fallback_used=bool(row.get("fallback_used", False)),
            )
            session.add(call)
            await session.commit()
    except Exception:
        logger.exception("could not record the llm call")


class UsageRepository:
    """Repository for querying LLM call usage and cost metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_day(self, days: int = 7) -> list[dict[str, Any]]:
        """Return aggregated token counts, calls, fallbacks, and costs per day."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        day_col = cast(LlmCall.created_at, Date).label("day")

        stmt = (
            select(
                day_col,
                func.count(LlmCall.id).label("calls"),
                func.coalesce(func.sum(LlmCall.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(LlmCall.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(LlmCall.cost_inr), 0.0).label("cost_inr"),
                func.coalesce(
                    func.sum(case((LlmCall.fallback_used.is_(True), 1), else_=0)),
                    0,
                ).label("fallbacks"),
                func.coalesce(
                    func.sum(case((LlmCall.status == "error", 1), else_=0)),
                    0,
                ).label("errors"),
            )
            .where(LlmCall.created_at >= cutoff)
            .group_by(day_col)
            .order_by(desc(day_col))
        )

        result = await self.session.execute(stmt)
        rows: list[dict[str, Any]] = []
        for r in result.all():
            rows.append(
                {
                    "date": str(r.day),
                    "calls": int(r.calls),
                    "tokens_in": int(r.tokens_in),
                    "tokens_out": int(r.tokens_out),
                    "cost_inr": round(float(r.cost_inr), 6),
                    "fallbacks": int(r.fallbacks),
                    "errors": int(r.errors),
                }
            )
        return rows
