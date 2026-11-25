"""Audit LLM gateway usage, latency percentiles, and cost against targets.

Run:
    uv run python scripts/llm_audit.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from peptalk.db.llm_calls import UsageRepository
from peptalk.db.models import LlmCall
from peptalk.db.session import session_scope


async def run_audit() -> None:
    print("=" * 70)
    print(" PEPTALK · LLM GATEWAY PRODUCTION AUDIT & METRICS REPORT")
    print("=" * 70)

    async with session_scope() as session:
        repo = UsageRepository(session)
        percentiles = await repo.latency_percentiles(7)

        stmt = select(LlmCall).order_by(LlmCall.id.desc())
        result = await session.execute(stmt)
        all_calls = list(result.scalars().all())

    total_calls = len(all_calls)
    ok_calls = [c for c in all_calls if c.status == "ok"]
    error_calls = [c for c in all_calls if c.status == "error"]
    fallback_calls = [c for c in all_calls if c.fallback_used]

    total_tokens_in = sum(c.tokens_in for c in all_calls)
    total_tokens_out = sum(c.tokens_out for c in all_calls)
    total_cost_inr = sum(float(c.cost_inr) for c in all_calls)

    gemini_calls = [c for c in all_calls if c.provider == "gemini"]
    groq_calls = [c for c in all_calls if c.provider == "groq"]

    avg_cost = total_cost_inr / len(ok_calls) if ok_calls else 0.0

    print("\n[1] Gateway Volume Summary (Last 7 Days):")
    print(f"  • Total LLM Invocations : {total_calls}")
    print(f"  • Successful (Status OK): {len(ok_calls)}")
    print(f"  • Provider Failures     : {len(error_calls)}")
    print(f"  • Fallbacks Triggered   : {len(fallback_calls)}")

    print("\n[2] Token & Cost Efficiency:")
    print(f"  • Input Tokens          : {total_tokens_in:,}")
    print(f"  • Output Tokens         : {total_tokens_out:,}")
    print(f"  • Total Cost (INR)      : Rs {total_cost_inr:.6f}")
    print(f"  • Avg Cost per Query    : Rs {avg_cost:.6f}")

    print("\n[3] Provider Routing Distribution:")
    gem_pct = len(gemini_calls) / max(total_calls, 1) * 100
    groq_pct = len(groq_calls) / max(total_calls, 1) * 100
    print(f"  • Gemini (Primary)      : {len(gemini_calls)} calls ({gem_pct:.1f}%)")
    print(f"  • Groq (Fallback)       : {len(groq_calls)} calls ({groq_pct:.1f}%)")

    print("\n[4] Latency Distribution (Measured on Successful Calls):")
    print(f"  • Total Sample Count    : {percentiles['count']}")
    print(f"  • Min Latency           : {percentiles['min_ms']} ms")
    print(f"  • p50 (Median)          : {percentiles['p50_ms']} ms")
    print(f"  • p90                   : {percentiles['p90_ms']} ms")
    print(f"  • p95                   : {percentiles['p95_ms']} ms")
    print(f"  • p99                   : {percentiles['p99_ms']} ms")

    print("\n[5] Target Evaluation:")
    target_latency = percentiles["p95_ms"] <= 6000.0
    target_cost = avg_cost <= 0.50

    lat_status = "PASS [OK]" if target_latency else "FAIL"
    cost_status = "PASS [OK]" if target_cost else "FAIL"
    p95_s = percentiles["p95_ms"] / 1000.0
    print(f"  • Day 1 NFR Target: p95 Latency < 6.0s  -> {lat_status} ({p95_s:.2f} s)")
    print(f"  • Target: Average Cost < Rs 0.50/query -> {cost_status} (Rs {avg_cost:.4f})")
    print("=" * 70)


def main() -> None:
    asyncio.run(run_audit())


if __name__ == "__main__":
    main()
