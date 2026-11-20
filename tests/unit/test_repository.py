"""Unit tests for the PostgreSQL DocumentRepository."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.db.models import Document, Page
from peptalk.db.repository import DocumentRepository, DocumentStoreAdapter, document_to_dict
from peptalk.store import DocumentStore

pytestmark = pytest.mark.anyio


def test_document_to_dict_serialization():
    """Verify document_to_dict serializes Document model fields and page 1 summary."""
    doc = Document(
        id="pep-0634",
        title="Structural Pattern Matching: Specification",
        source_url="https://peps.python.org/pep-0634/",
        licence=None,
        doc_type="PEP",
        published_on=date(2020, 9, 12),
        sha256="a" * 64,
        document_metadata={
            "pep_number": 634,
            "status": "Final",
            "python_version": "3.10",
        },
    )
    doc.pages = [Page(doc_id="pep-0634", page_no=1, text="Specifies match syntax.")]

    serialized = document_to_dict(doc)

    assert serialized["id"] == "pep-0634"
    assert serialized["title"] == "Structural Pattern Matching: Specification"
    assert serialized["type"] == "PEP"
    assert serialized["created"] == "2020-09-12"
    assert serialized["summary"] == "Specifies match syntax."
    assert serialized["pep_number"] == 634
    assert serialized["status"] == "Final"
    assert serialized["python_version"] == "3.10"


def test_document_to_dict_empty_pages_resilient_summary():
    """Verify document_to_dict defaults summary to empty string when pages list is empty."""
    doc = Document(
        id="pep-0001",
        title="PEP Purpose and Guidelines",
        source_url="https://peps.python.org/pep-0001/",
        licence=None,
        doc_type="PEP",
        published_on=None,
        sha256="b" * 64,
        document_metadata={},
    )
    doc.pages = []

    serialized = document_to_dict(doc)
    assert serialized["id"] == "pep-0001"
    assert serialized["summary"] == ""


async def test_repository_get_by_id_found():
    """Verify repository get_by_id returns serialized dict when document exists."""
    mock_doc = MagicMock(spec=Document)
    mock_doc.id = "pep-0634"
    mock_doc.title = "Pattern Matching"
    mock_doc.source_url = "https://peps.python.org/pep-0634/"
    mock_doc.licence = None
    mock_doc.doc_type = "PEP"
    mock_doc.published_on = date(2020, 9, 12)
    mock_doc.document_metadata = {"status": "Final"}
    mock_doc.pages = [MagicMock(spec=Page, page_no=1, text="Page 1 text")]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    repo = DocumentRepository(mock_session)
    result = await repo.get_by_id("pep-0634")

    assert result is not None
    assert result["id"] == "pep-0634"
    assert result["summary"] == "Page 1 text"
    mock_session.execute.assert_awaited_once()


async def test_repository_get_by_id_not_found():
    """Verify repository get_by_id returns None when document does not exist."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    repo = DocumentRepository(mock_session)
    result = await repo.get_by_id("non-existent")

    assert result is None
    mock_session.execute.assert_awaited_once()


async def test_repository_list_documents_filtering_and_pagination():
    """Verify repository list_documents constructs queries with filters and pagination."""
    mock_doc = MagicMock(spec=Document)
    mock_doc.id = "pep-0634"
    mock_doc.title = "Pattern Matching"
    mock_doc.source_url = "https://peps.python.org/pep-0634/"
    mock_doc.licence = None
    mock_doc.doc_type = "PEP"
    mock_doc.published_on = date(2020, 9, 12)
    mock_doc.document_metadata = {"status": "Final", "python_version": "3.10"}
    mock_doc.pages = []

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    docs_result = MagicMock()
    docs_result.scalars.return_value.all.return_value = [mock_doc]

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = [count_result, docs_result]

    repo = DocumentRepository(mock_session)
    items, total = await repo.list_documents(
        limit=10,
        offset=0,
        doc_type="PEP",
        python_version="3.10",
        status="Final",
        pep_number=634,
    )

    assert total == 1
    assert len(items) == 1
    assert items[0]["id"] == "pep-0634"
    assert mock_session.execute.await_count == 2


async def test_repository_list_documents_short_circuits_on_zero_total():
    """Verify list_documents avoids secondary fetch query when total count is 0."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = count_result

    repo = DocumentRepository(mock_session)
    items, total = await repo.list_documents(doc_type="NonExistent")

    assert total == 0
    assert items == []
    assert mock_session.execute.await_count == 1


async def test_document_store_adapter():
    """Verify DocumentStoreAdapter adapts DocumentStore to repository protocol."""
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    doc = await adapter.get_by_id("pep-0634")
    assert doc is not None
    assert doc["id"] == "pep-0634"

    items, total = await adapter.list_documents(
        limit=5,
        offset=0,
        python_version="3.10",
        status="Final",
    )
    assert total >= 1
    assert len(items) <= 5
    assert all(item.get("python_version") == "3.10" for item in items)


async def test_repository_exists():
    """Verify repository exists returns True when document exists and False otherwise."""
    mock_result_found = MagicMock()
    mock_result_found.scalar_one.return_value = 1
    mock_result_not_found = MagicMock()
    mock_result_not_found.scalar_one.return_value = 0

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = [mock_result_found, mock_result_not_found]

    repo = DocumentRepository(mock_session)
    assert await repo.exists("pep-0634") is True
    assert await repo.exists("pep-9999") is False


async def test_repository_count_documents():
    """Verify repository count_documents executes count query with filters."""
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    repo = DocumentRepository(mock_session)
    count = await repo.count_documents(doc_type="PEP", status="Final")

    assert count == 42
    mock_session.execute.assert_awaited_once()


async def test_document_store_adapter_exists_and_count():
    """Verify adapter implements exists and count_documents methods."""
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    assert await adapter.exists("pep-0634") is True
    assert await adapter.exists("non-existent-doc") is False

    count = await adapter.count_documents(python_version="3.10")
    assert count >= 1


async def test_repository_search_documents():
    """Verify repository search_documents constructs case-insensitive filter query."""
    mock_doc = MagicMock(spec=Document)
    mock_doc.id = "pep-0634"
    mock_doc.title = "Structural Pattern Matching"
    mock_doc.source_url = "https://peps.python.org/pep-0634/"
    mock_doc.licence = None
    mock_doc.doc_type = "PEP"
    mock_doc.published_on = None
    mock_doc.document_metadata = {}
    mock_doc.pages = []

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    docs_result = MagicMock()
    docs_result.scalars.return_value.all.return_value = [mock_doc]

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = [count_result, docs_result]

    repo = DocumentRepository(mock_session)
    items, total = await repo.search_documents("Pattern Matching")

    assert total == 1
    assert len(items) == 1
    assert items[0]["id"] == "pep-0634"


async def test_document_store_adapter_search():
    """Verify DocumentStoreAdapter searches by keyword in title or id."""
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    items, total = await adapter.search_documents("pattern matching")
    assert total >= 1
    assert any("pattern" in d.get("title", "").lower() for d in items)
