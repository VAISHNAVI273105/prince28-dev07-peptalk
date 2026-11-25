"""PostgreSQL document repository for querying documents and pages."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from peptalk.db.models import Document, Page


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
        if page_1 and page_1.text:
            data["summary"] = page_1.text
        else:
            data.setdefault("summary", "")
    else:
        data.setdefault("summary", "")

    return data


def format_document_citation(doc: dict[str, Any]) -> dict[str, str]:
    """Format standard citation metadata and markdown reference from document dictionary.

    Returns a dict with 'id', 'title', 'url', 'markdown_link', and 'reference'.
    """
    doc_id = str(doc.get("id", "unknown"))
    title = str(doc.get("title", doc_id))
    url = str(doc.get("source_url", ""))
    pep_num = doc.get("pep_number")

    label = f"PEP {pep_num}: {title}" if pep_num is not None else title
    md_link = f"[{label}]({url})" if url else label

    return {
        "id": doc_id,
        "title": title,
        "url": url,
        "markdown_link": md_link,
        "reference": label,
    }


SUPPORTED_PYTHON_VERSIONS: frozenset[str] = frozenset(
    {"3.8", "3.9", "3.10", "3.11", "3.12", "3.13"}
)


def is_supported_python_version(version: str) -> bool:
    """Check if the provided string is an active or supported Python minor version.

    Supports CPython versions 3.8 through 3.13.
    """
    if not version or not isinstance(version, str):
        return False
    return version.strip() in SUPPORTED_PYTHON_VERSIONS


class DocumentRepositoryProtocol(Protocol):
    """Protocol defining the document repository interface."""

    async def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Retrieve a document by ID."""
        ...

    async def exists(self, document_id: str) -> bool:
        """Check whether a document exists by ID."""
        ...

    async def count_documents(
        self,
        *,
        doc_type: str | None = None,
        python_version: str | None = None,
        status: str | None = None,
        pep_number: int | None = None,
    ) -> int:
        """Count total documents matching given filter criteria."""
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

    async def search_documents(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search documents by title or identifier using case-insensitive matching."""
        ...

    async def get_page(self, document_id: str, page_no: int) -> dict[str, Any] | None:
        """Retrieve a specific page for a document by document ID and page number."""
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

    async def exists(self, document_id: str) -> bool:
        """Check whether a document exists by its ID without loading relations."""
        stmt = select(func.count()).select_from(Document).where(Document.id == document_id)
        result = await self.session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def count_documents(
        self,
        *,
        doc_type: str | None = None,
        python_version: str | None = None,
        status: str | None = None,
        pep_number: int | None = None,
    ) -> int:
        """Count total documents matching given filter criteria."""
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

        stmt = select(func.count()).select_from(Document)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar_one()

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

        # Total count query
        count_stmt = select(func.count()).select_from(Document)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        if total == 0 or offset >= total:
            return [], total

        # Paginated query with eager loading of pages
        stmt = (
            select(Document)
            .options(selectinload(Document.pages))
            .order_by(Document.id.asc())
            .limit(limit)
            .offset(offset)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        result = await self.session.execute(stmt)
        docs = result.scalars().all()

        items = [document_to_dict(doc) for doc in docs]
        return items, total

    async def search_documents(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search documents by title or identifier using case-insensitive matching."""
        term = query.strip()
        if not term:
            return await self.list_documents(limit=limit, offset=offset)

        search_filter = or_(
            Document.title.ilike(f"%{term}%"),
            Document.id.ilike(f"%{term}%"),
        )
        count_stmt = select(func.count()).select_from(Document).where(search_filter)
        total = (await self.session.execute(count_stmt)).scalar_one()

        if total == 0 or offset >= total:
            return [], total

        stmt = (
            select(Document)
            .options(selectinload(Document.pages))
            .where(search_filter)
            .order_by(Document.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        docs = result.scalars().all()
        return [document_to_dict(d) for d in docs], total

    async def get_page(self, document_id: str, page_no: int) -> dict[str, Any] | None:
        """Retrieve a specific page for a document by document ID and page number."""
        stmt = select(Page).where(Page.doc_id == document_id, Page.page_no == page_no)
        result = await self.session.execute(stmt)
        page = result.scalar_one_or_none()
        if page is None:
            return None
        return {
            "document_id": page.doc_id,
            "page_no": page.page_no,
            "text": page.text,
            "headings": list(page.headings or []),
        }


class DocumentStoreAdapter:
    """Adapter wrapping DocumentStore to match DocumentRepositoryProtocol."""

    def __init__(self, store: Any) -> None:
        self.store = store

    async def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        return self.store.get_by_id(document_id)

    async def exists(self, document_id: str) -> bool:
        """Check whether a document exists in the store by its ID."""
        return self.store.get_by_id(document_id) is not None

    async def count_documents(
        self,
        *,
        doc_type: str | None = None,
        python_version: str | None = None,
        status: str | None = None,
        pep_number: int | None = None,
    ) -> int:
        """Count total documents matching given filter criteria."""
        items = self.store.get_all()
        if doc_type is not None:
            items = [d for d in items if d.get("type") == doc_type]
        if python_version is not None:
            items = [d for d in items if d.get("python_version") == python_version]
        if status is not None:
            items = [d for d in items if d.get("status") == status]
        if pep_number is not None:
            items = [d for d in items if d.get("pep_number") == pep_number]
        return len(items)

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
        if total == 0 or offset >= total:
            return [], total
        return items[offset : offset + limit], total

    async def search_documents(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search documents by title or identifier in memory."""
        term = query.strip().lower()
        if not term:
            return await self.list_documents(limit=limit, offset=offset)

        matching = [
            d
            for d in self.store.get_all()
            if term in str(d.get("title", "")).lower()
            or term in str(d.get("id", "")).lower()
            or term in str(d.get("summary", "")).lower()
        ]
        total = len(matching)
        if total == 0 or offset >= total:
            return [], total
        return matching[offset : offset + limit], total

    async def get_page(self, document_id: str, page_no: int) -> dict[str, Any] | None:
        """Retrieve a page from in-memory document store."""
        doc = self.store.get_by_id(document_id)
        if doc is None:
            return None
        if page_no == 1:
            return {
                "document_id": document_id,
                "page_no": 1,
                "text": str(doc.get("summary", "")),
                "headings": [],
            }
        return None
