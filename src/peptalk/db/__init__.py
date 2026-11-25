"""Database foundation for PEPTalk."""

from peptalk.db.base import Base
from peptalk.db.llm_calls import UsageRepository, record_call
from peptalk.db.models import Document, LlmCall, Page, ParseFailure
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
    "LlmCall",
    "Page",
    "ParseFailure",
    "UsageRepository",
    "record_call",
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
