"""PostgreSQL document repository for querying documents and pages."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from peptalk.db.models import Document


def document_to_dict(doc: Document) -> dict[str, Any]:
    """Serialize a Document model and its first page to a dictionary."""
    data: dict[str, Any] = {
        "id": doc.id,
        "title": doc.title,
        "type": doc.doc_type,
        "source_url": doc.source_url,
    }
    data["created"] = doc.published_on.isoformat() if doc.published_on else None
    if doc.licence:
        data["licence"] = doc.licence

    if doc.document_metadata:
        data.update(doc.document_metadata)

    if doc.pages:
        page_1 = next((p for p in doc.pages if p.page_no == 1), None)
        if page_1:
            data["summary"] = page_1.text

    return data


class DocumentRepositoryProtocol(Protocol):
    """Protocol defining the document repository interface."""

    async def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Retrieve a document by ID."""
        ...

    async def list_documents(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        doc_type: str | None = None,
        python_version: str | None = None,
        status: str | None = None,
        pep_number: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List documents matching filters with pagination."""
        ...


class DocumentRepository:
    """Asynchronous repository for Document queries against PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Retrieve a single document by its ID."""
        stmt = (
            select(Document).options(selectinload(Document.pages)).where(Document.id == document_id)
        )
        result = await self.session.execute(stmt)
        doc = result.scalar_one_or_none()
        if doc is None:
            return None
        return document_to_dict(doc)

    async def list_documents(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        doc_type: str | None = None,
        python_version: str | None = None,
        status: str | None = None,
        pep_number: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List documents matching filters with pagination."""
        conditions = []

        if doc_type is not None:
            conditions.append(Document.doc_type == doc_type)

        if python_version is not None:
            conditions.append(
                Document.document_metadata.contains({"python_version": python_version})
            )

        if status is not None:
            conditions.append(Document.document_metadata.contains({"status": status}))

        if pep_number is not None:
            conditions.append(Document.document_metadata.contains({"pep_number": pep_number}))

        where_clause = and_(*conditions) if conditions else True

        # Total count query
        count_stmt = select(func.count()).select_from(Document).where(where_clause)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Paginated query with eager loading of pages
        stmt = (
            select(Document)
            .options(selectinload(Document.pages))
            .where(where_clause)
            .order_by(Document.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        docs = result.scalars().all()

        items = [document_to_dict(doc) for doc in docs]
        return items, total


class DocumentStoreAdapter:
    """Adapter wrapping DocumentStore to match DocumentRepositoryProtocol."""

    def __init__(self, store: Any) -> None:
        self.store = store

    async def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        return self.store.get_by_id(document_id)

    async def list_documents(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        doc_type: str | None = None,
        python_version: str | None = None,
        status: str | None = None,
        pep_number: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        items = self.store.get_all()
        if doc_type is not None:
            items = [d for d in items if d.get("type") == doc_type]
        if python_version is not None:
            items = [d for d in items if d.get("python_version") == python_version]
        if status is not None:
            items = [d for d in items if d.get("status") == status]
        if pep_number is not None:
            items = [d for d in items if d.get("pep_number") == pep_number]

        total = len(items)
        return items[offset : offset + limit], total
