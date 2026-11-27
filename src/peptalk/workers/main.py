"""Worker settings and lifecycle hooks for arq."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy import update

from peptalk.config import get_settings
from peptalk.db.models import IngestItem
from peptalk.db.session import create_async_db_engine, create_async_session_factory
from peptalk.llm.doc_meta import DocMeta
from peptalk.llm.gateway import build_gateway
from peptalk.llm.prompts import load_prompt
from peptalk.workers.ingest import Pace, ingest_document
from peptalk.workers.queue import redis_settings_from_url

logger = logging.getLogger("peptalk.worker")


async def on_startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    ctx["settings"] = settings
    db_url = settings.database_url.get_secret_value() if settings.database_url else ""
    engine = create_async_db_engine(db_url)
    ctx["engine"] = engine
    sessionmaker = create_async_session_factory(engine)
    ctx["sessionmaker"] = sessionmaker
    ctx["http"] = httpx.AsyncClient(timeout=30.0)
    ctx["pace"] = Pace(settings.ingest_rpm)
    ctx["gateway"] = build_gateway(settings)

    try:
        prompt, ver = load_prompt("extract", prompts_dir=settings.prompts_dir)
        ctx["extract"] = {
            "schema": DocMeta,
            "prompt": prompt,
            "version": ver,
            "chars": 6000,
        }
    except Exception:
        ctx["extract"] = None

    # On startup: put any items left 'running' back to 'queued' so interrupted work is retried
    async with sessionmaker() as session:
        result = await session.execute(
            update(IngestItem)
            .where(IngestItem.status == "running")
            .values(status="queued")
            .returning(IngestItem.id)
        )
        requeued = result.scalars().all()
        await session.commit()
        logger.info("worker ready, %d unfinished item(s) put back in the queue", len(requeued))


async def on_shutdown(ctx: dict[str, Any]) -> None:
    if "http" in ctx:
        await ctx["http"].aclose()
    if "engine" in ctx:
        await ctx["engine"].dispose()


class WorkerSettings:
    functions = [ingest_document]
    on_startup = on_startup
    on_shutdown = on_shutdown
    settings = get_settings()
    max_jobs = settings.ingest_concurrency
    job_timeout = settings.ingest_job_timeout
    redis_settings = redis_settings_from_url(settings.redis_url)
