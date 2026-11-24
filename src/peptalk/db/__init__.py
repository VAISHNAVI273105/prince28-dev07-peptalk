"""Database foundation for PEPTalk."""

from peptalk.db.base import Base
from peptalk.db.models import Document, Page, ParseFailure
from peptalk.db.repository import (
    DocumentRepository,
    DocumentRepositoryProtocol,
    DocumentStoreAdapter,
    document_to_dict,
)
from peptalk.db.session import (
    create_async_db_engine,
    create_async_session_factory,
    dispose_engine,
    get_async_engine,
    get_db_session,
    get_session_factory,
    normalize_async_database_url,
    reset_engine,
    session_scope,
)

__all__ = [
    "Base",
    "Document",
    "DocumentRepository",
    "DocumentRepositoryProtocol",
    "DocumentStoreAdapter",
    "Page",
    "ParseFailure",
    "create_async_db_engine",
    "create_async_session_factory",
    "dispose_engine",
    "document_to_dict",
    "get_async_engine",
    "get_db_session",
    "get_session_factory",
    "normalize_async_database_url",
    "reset_engine",
    "session_scope",
]
