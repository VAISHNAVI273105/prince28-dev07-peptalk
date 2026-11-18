"""Execute and analyze EXPLAIN query plans for JSONB GIN index on PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from sqlalchemy import text

from peptalk.config import get_settings
from peptalk.db.session import dispose_engine, session_scope

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("explain")


async def explain_query(json_filter_str: str) -> None:
    """Run EXPLAIN (ANALYZE, BUFFERS) for normal and forced-index execution paths."""
    settings = get_settings()
    if not settings.database_url:
        logger.error("DATABASE_URL is not configured.")
        return

    query_sql = (
        "EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING, SUMMARY) "
        "SELECT id, title, metadata FROM documents "
        "WHERE metadata @> :filter::jsonb;"
    )

    async with session_scope() as session:
        print("=" * 80)
        print("EXPLAIN ANALYSIS: JSONB CONTAINMENT QUERY")
        print(f"Predicate: metadata @> '{json_filter_str}'::jsonb")
        print("=" * 80)

        # Plan 1: Default Planner Evaluation
        print("\n--- 1. DEFAULT QUERY PLAN (Planner Auto-Optimization) ---")
        try:
            res_default = await session.execute(text(query_sql), {"filter": json_filter_str})
            lines_default = [row[0] for row in res_default.fetchall()]
            for line in lines_default:
                print(f"  {line}")
        except Exception as exc:
            print(f"  Execution failed: {exc}")

        # Plan 2: Forced Index Demonstration (enable_seqscan = off)
        print("\n--- 2. FORCED INDEX SCAN DEMONSTRATION (enable_seqscan = off) ---")
        try:
            await session.execute(text("SET LOCAL enable_seqscan = off;"))
            res_forced = await session.execute(text(query_sql), {"filter": json_filter_str})
            lines_forced = [row[0] for row in res_forced.fetchall()]
            for line in lines_forced:
                print(f"  {line}")
        except Exception as exc:
            print(f"  Execution failed: {exc}")

        print("\n" + "=" * 80)
        print("ARCHITECTURAL EXPLANATION & QUERY PLAN ANALYSIS:")
        print("=" * 80)
        print(
            "1. Small-Table Cost Optimization:\n"
            "   For a small dataset (e.g. 20-22 rows), the entire table resides in a single\n"
            "   8KB buffer page. A sequential scan requires reading exactly 1 page directly into\n"
            "   cache, yielding an estimated cost around 1.0 - 1.3.\n"
            "   In contrast, a GIN index lookup requires reading GIN index pages, building an\n"
            "   in-memory bitmap, and then performing a bitmap heap scan to access the data page,\n"
            "   which carries an estimated startup cost of 8.0 - 12.0.\n"
            "   Therefore, PostgreSQL's cost-based query optimizer correctly chooses a sequential\n"
            "   scan as the fastest and most efficient access path for small tables.\n"
            "\n"
            "2. GIN Index Verification (ix_documents_metadata_gin):\n"
            "   When sequential scan is disabled (enable_seqscan = off), or as the dataset grows\n"
            "   to thousands of records, the planner switches to a Bitmap Index Scan\n"
            "   on 'ix_documents_metadata_gin'.\n"
            "\n"
            "3. Bitmap Index Scan & Bitmap Heap Scan Mechanics:\n"
            "   - 'Bitmap Index Scan on ix_documents_metadata_gin': Walks the GIN index using\n"
            "     'jsonb_path_ops' to evaluate containment paths, constructing a bitmask of\n"
            "     page and tuple pointers matching the query predicate.\n"
            "   - 'Bitmap Heap Scan on documents': Reads physical heap pages in sequential disk\n"
            "     order using the bitmap, eliminating random I/O and applying recheck conditions.\n"
        )
        print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explain JSONB GIN index queries on PEPTalk documents."
    )
    parser.add_argument(
        "--version",
        default="3.10",
        help="Python version to query (default: 3.10)",
    )
    args = parser.parse_args()

    filter_dict = {"python_version": args.version}
    filter_json = json.dumps(filter_dict)

    try:
        asyncio.run(explain_query(filter_json))
    finally:
        asyncio.run(dispose_engine())


if __name__ == "__main__":
    main()
