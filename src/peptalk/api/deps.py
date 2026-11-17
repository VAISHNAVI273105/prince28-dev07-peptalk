from typing import Annotated

from fastapi import Depends

from peptalk.config import Settings, get_settings
from peptalk.store import DocumentStore


def get_document_store(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentStore:
    """Dependency provider returning a DocumentStore configured with app settings."""
    return DocumentStore(settings.data_file)
