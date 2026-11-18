from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.config import Settings, get_settings
from peptalk.db.repository import (
    DocumentRepository,
    DocumentRepositoryProtocol,
    DocumentStoreAdapter,
)
from peptalk.db.session import get_db_session, session_scope
from peptalk.store import DocumentStore


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


__all__ = [
    "check_database_readiness",
    "get_db_session",
    "get_document_repository",
    "get_document_store",
]
