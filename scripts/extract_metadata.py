"""CLI command to extract structured metadata from parsed documents using LLM."""

import argparse
import asyncio
import time

from peptalk.config import get_settings
from peptalk.db.llm_calls import record_call
from peptalk.db.session import create_async_db_engine, create_async_session_factory
from peptalk.llm.doc_meta import DocMeta
from peptalk.llm.extract import run
from peptalk.llm.gateway import build_gateway
from peptalk.llm.prompts import load_prompt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured metadata from parsed documents."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of documents to extract (default: 0 = all pending).",
    )
    parser.add_argument(
        "--rpm",
        type=float,
        default=12.0,
        help="Rate limit in requests per minute (default: 12.0).",
    )
    parser.add_argument(
        "--chars",
        type=int,
        default=6000,
        help="Maximum characters of document text sent to model (default: 6000).",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Also retry documents that previously failed extraction.",
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Enforce native JSON schema on provider API call if supported.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Prompt version to use (e.g. 'v1', 'v2'). Defaults to latest version.",
    )
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    settings = get_settings()
    if not settings.database_url:
        raise ValueError("DATABASE_URL must be configured to run extraction.")

    engine = create_async_db_engine(settings.database_url)
    sessionmaker = create_async_session_factory(engine)
    try:
        gateway = build_gateway(settings, recorder=record_call)

        prompt_text, prompt_version = load_prompt(
            "extract", version=args.version, prompts_dir=settings.prompts_dir
        )

        start = time.perf_counter()
        counts = await run(
            sessionmaker=sessionmaker,
            gateway=gateway,
            schema=DocMeta,
            prompt=prompt_text,
            version=prompt_version,
            limit=args.limit,
            rpm=args.rpm,
            chars=args.chars,
            retry_failed=args.retry_failed,
            native=args.native,
        )
        duration = int(time.perf_counter() - start)
        cost = counts["micro_inr"] / 1_000_000

        print(
            f"prompt={prompt_version} pending={counts['pending']} ok={counts['ok']} "
            f"repaired={counts['repaired']} failed={counts['failed']} "
            f"tokens_in={counts['tokens_in']} tokens_out={counts['tokens_out']} "
            f"cost=Rs {cost:.4f} seconds={duration}"
        )
    finally:
        await engine.dispose()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
