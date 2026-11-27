"""The only file that talks to Redis."""

from __future__ import annotations

from typing import Protocol

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings


class QueueProtocol(Protocol):
    async def put(self, item_ids: list[int]) -> None: ...


class IngestQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self.pool = pool

    async def put(self, item_ids: list[int]) -> None:
        for item_id in item_ids:
            await self.pool.enqueue_job("ingest_document", item_id)


def redis_settings_from_url(url: str) -> RedisSettings:
    return RedisSettings.from_dsn(url)


async def open_queue(redis_url: str) -> IngestQueue:
    settings = redis_settings_from_url(redis_url)
    pool = await create_pool(settings)
    return IngestQueue(pool)
