from typing import Annotated

from fastapi import Depends

from peptalk.config import Settings, get_settings
from peptalk.db.session import get_db_session
from peptalk.store import DocumentStore


def get_document_store(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentStore:
    """Dependency provider returning a DocumentStore configured with app settings."""
    return DocumentStore(settings.data_file)


__all__ = ["get_db_session", "get_document_store"]
