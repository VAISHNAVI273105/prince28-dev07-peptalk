"""Database foundation for PEPTalk."""

from peptalk.db.base import Base
from peptalk.db.models import Document, Page

__all__ = ["Base", "Document", "Page"]
