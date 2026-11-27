"""Dependencies for FastAPI routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.config import Settings, get_settings
from peptalk.db.ingest_jobs import IngestRepository
from peptalk.db.llm_calls import UsageRepository
from peptalk.db.repository import (
    DocumentRepository,
    DocumentRepositoryProtocol,
    DocumentStoreAdapter,
)
from peptalk.db.session import get_db_session, session_scope
from peptalk.llm.gateway import LLMGateway
from peptalk.store import DocumentStore
from peptalk.workers.queue import QueueProtocol, open_queue


def get_document_store(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentStore:
    """Dependency provider returning a DocumentStore configured with app settings."""
    return DocumentStore(settings.data_file)


async def get_document_repository(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepositoryProtocol:
    """Dependency provider returning a document repository."""
    if get_document_store in request.app.dependency_overrides:
        store = request.app.dependency_overrides[get_document_store]()
        return DocumentStoreAdapter(store)
    return DocumentRepository(session)


async def check_database_readiness(
    settings: Annotated[Settings, Depends(get_settings)],
) -> bool:
    """Verify database connectivity by executing a ping query."""
    if not settings.database_url:
        return False
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_gateway(request: Request) -> LLMGateway:
    """Dependency provider returning the LLM gateway instance from app state."""
    return request.app.state.gateway


def get_usage_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UsageRepository:
    """Dependency provider returning a UsageRepository for metrics queries."""
    return UsageRepository(session)


async def get_ingest_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IngestRepository:
    """Dependency provider returning an IngestRepository for job and item queries."""
    return IngestRepository(session)


def get_manifest(settings: Annotated[Settings, Depends(get_settings)]) -> list[dict]:
    """Dependency provider returning parsed manifest records."""
    if not settings.manifest_file.exists():
        return []
    records = []
    with settings.manifest_file.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


async def get_queue(
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
) -> QueueProtocol:
    """Dependency provider returning the Redis job queue."""
    queue = getattr(request.app.state, "queue", None)
    if queue is None:
        try:
            queue = await open_queue(settings.redis_url)
            request.app.state.queue = queue
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="The job queue (Redis) cannot be reached.",
            ) from exc
    return queue


async def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    """Require valid administrative token header for mutative batch ingestion."""
    if not settings.admin_token:
        raise HTTPException(status_code=403, detail="Set ADMIN_TOKEN to allow ingestion here.")
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Missing or wrong X-Admin-Token header.")


GatewayDep = Annotated[LLMGateway, Depends(get_gateway)]
UsageDep = Annotated[UsageRepository, Depends(get_usage_repository)]
IngestRepoDep = Annotated[IngestRepository, Depends(get_ingest_repository)]
ManifestDep = Annotated[list[dict], Depends(get_manifest)]
QueueDep = Annotated[QueueProtocol, Depends(get_queue)]

__all__ = [
    "GatewayDep",
    "IngestRepoDep",
    "ManifestDep",
    "QueueDep",
    "UsageDep",
    "check_database_readiness",
    "get_db_session",
    "get_document_repository",
    "get_document_store",
    "get_gateway",
    "get_ingest_repository",
    "get_manifest",
    "get_queue",
    "get_usage_repository",
    "require_admin",
]
