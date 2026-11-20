"""Unit tests for the idempotent JSON-to-PostgreSQL document loader."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.db.models import Document, Page
from scripts.load_db import (
    LoadStats,
    compute_canonical_sha256,
    load_documents_from_json,
    load_record,
    map_record_to_document_and_page,
)

pytestmark = pytest.mark.anyio


def test_compute_canonical_sha256_key_order_independence():
    """Verify canonical sha256 is identical regardless of dictionary key ordering."""
    record_a = {"id": "pep-001", "title": "First", "status": "Final"}
    record_b = {"status": "Final", "id": "pep-001", "title": "First"}
    assert compute_canonical_sha256(record_a) == compute_canonical_sha256(record_b)


def test_compute_canonical_sha256_differs_on_content_change():
    """Verify different record contents produce different SHA-256 hashes."""
    record_a = {"id": "pep-001", "title": "First"}
    record_b = {"id": "pep-001", "title": "Second"}
    assert compute_canonical_sha256(record_a) != compute_canonical_sha256(record_b)


def test_map_record_to_document_and_page():
    """Verify raw JSON record is accurately mapped to Document and Page structures."""
    sample = {
        "id": "pep-0634",
        "pep_number": 634,
        "title": "Structural Pattern Matching: Specification",
        "status": "Final",
        "type": "PEP",
        "python_version": "3.10",
        "created": "2020-09-12",
        "source_url": "https://peps.python.org/pep-0634/",
        "summary": "Specifies pattern matching syntax.",
    }

    doc_attrs, page_attrs = map_record_to_document_and_page(sample)

    assert doc_attrs["id"] == "pep-0634"
    assert doc_attrs["title"] == "Structural Pattern Matching: Specification"
    assert doc_attrs["source_url"] == "https://peps.python.org/pep-0634/"
    assert doc_attrs["doc_type"] == "PEP"
    assert doc_attrs["published_on"] == date(2020, 9, 12)
    assert len(doc_attrs["sha256"]) == 64
    assert doc_attrs["document_metadata"] == {
        "pep_number": 634,
        "status": "Final",
        "python_version": "3.10",
    }

    assert page_attrs["doc_id"] == "pep-0634"
    assert page_attrs["page_no"] == 1
    assert page_attrs["text"] == "Specifies pattern matching syntax."


async def test_load_record_inserts_new():
    """Verify load_record inserts new Document and Page when document does not exist."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    record = {
        "id": "pep-0634",
        "title": "Pattern Matching",
        "source_url": "https://peps.python.org/pep-0634/",
        "type": "PEP",
        "created": "2020-09-12",
        "summary": "Pattern matching syntax.",
    }

    status = await load_record(mock_session, record)
    assert status == "inserted"

    assert mock_session.add.call_count == 2
    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    assert any(isinstance(obj, Document) and obj.id == "pep-0634" for obj in added_objects)
    assert any(isinstance(obj, Page) and obj.doc_id == "pep-0634" for obj in added_objects)


async def test_load_record_skips_unchanged():
    """Verify load_record skips unmodified documents when SHA-256 matches."""
    record = {
        "id": "pep-0634",
        "title": "Pattern Matching",
        "source_url": "https://peps.python.org/pep-0634/",
        "type": "PEP",
        "created": "2020-09-12",
        "summary": "Pattern matching syntax.",
    }
    expected_hash = compute_canonical_sha256(record)

    mock_doc = MagicMock(spec=Document)
    mock_doc.id = "pep-0634"
    mock_doc.sha256 = expected_hash

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = mock_doc

    status = await load_record(mock_session, record)
    assert status == "skipped"
    mock_session.add.assert_not_called()


async def test_load_record_updates_when_hash_differs():
    """Verify load_record updates Document and Page text when content has changed."""
    record = {
        "id": "pep-0634",
        "title": "Pattern Matching Updated",
        "source_url": "https://peps.python.org/pep-0634/",
        "type": "PEP",
        "created": "2020-09-12",
        "summary": "Updated summary text.",
    }

    mock_doc = MagicMock(spec=Document)
    mock_doc.id = "pep-0634"
    mock_doc.sha256 = "old_stale_hash_value"

    mock_page = MagicMock(spec=Page)
    mock_page.doc_id = "pep-0634"
    mock_page.page_no = 1
    mock_page.text = "Old summary."

    mock_session = AsyncMock(spec=AsyncSession)

    async def mock_get(entity, ident):
        if entity is Document:
            return mock_doc
        if entity is Page:
            return mock_page
        return None

    mock_session.get.side_effect = mock_get

    status = await load_record(mock_session, record)
    assert status == "updated"

    assert mock_doc.title == "Pattern Matching Updated"
    assert mock_doc.sha256 == compute_canonical_sha256(record)
    assert mock_page.text == "Updated summary text."


async def test_load_documents_from_json_orchestration(tmp_path: Path):
    """Verify load_documents_from_json reads file, counts stats, and commits."""
    test_file = tmp_path / "records.json"
    records = [
        {"id": "doc-1", "title": "Doc One", "source_url": "https://a.com", "summary": "One"},
        {"id": "doc-2", "title": "Doc Two", "source_url": "https://b.com", "summary": "Two"},
    ]
    test_file.write_text(json.dumps(records), encoding="utf-8")

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    stats = await load_documents_from_json(test_file, mock_session)

    assert isinstance(stats, LoadStats)
    assert stats.total == 2
    assert stats.inserted == 2
    assert stats.updated == 0
    assert stats.skipped == 0
    assert stats.errors == 0
    mock_session.commit.assert_awaited_once()


async def test_load_documents_missing_file_raises_error(tmp_path: Path):
    """Verify attempting to load a non-existent JSON file raises FileNotFoundError."""
    missing = tmp_path / "non_existent.json"
    mock_session = AsyncMock(spec=AsyncSession)

    with pytest.raises(FileNotFoundError, match="JSON source file not found"):
        await load_documents_from_json(missing, mock_session)


def test_validate_pep_status():
    """Verify validate_pep_status normalizes standard PEP statuses and handles edge cases."""
    from scripts.load_db import validate_pep_status

    assert validate_pep_status("final") == "Final"
    assert validate_pep_status("DRAFT") == "Draft"
    assert validate_pep_status("Active") == "Active"
    assert validate_pep_status("superseded") == "Superseded"
    assert validate_pep_status(None) is None
    assert validate_pep_status("") is None
    assert validate_pep_status("CustomStatus") == "CustomStatus"


async def test_load_documents_graceful_malformed_record_handling(tmp_path: Path):
    """Verify malformed records without ID are skipped and counted in stats.errors."""
    test_file = tmp_path / "records_with_malformed.json"
    records = [
        {"id": "valid-1", "title": "Valid One", "source_url": "https://a.com", "summary": "One"},
        {"title": "Missing ID", "source_url": "https://b.com"},  # Malformed: no id
        {"id": "", "title": "Empty ID", "source_url": "https://c.com"},  # Malformed: empty id
        {"id": "valid-2", "title": "Valid Two", "source_url": "https://d.com", "summary": "Two"},
    ]
    test_file.write_text(json.dumps(records), encoding="utf-8")

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    stats = await load_documents_from_json(test_file, mock_session, fail_fast=False)

    assert stats.total == 4
    assert stats.inserted == 2
    assert stats.errors == 2
    mock_session.commit.assert_awaited_once()


async def test_load_documents_fail_fast_raises_error(tmp_path: Path):
    """Verify fail_fast=True raises ValueError on encountering malformed record."""
    test_file = tmp_path / "records_bad.json"
    records = [{"title": "No ID"}]
    test_file.write_text(json.dumps(records), encoding="utf-8")

    mock_session = AsyncMock(spec=AsyncSession)

    with pytest.raises(ValueError, match="missing required 'id'"):
        await load_documents_from_json(test_file, mock_session, fail_fast=True)


def test_validate_python_version():
    """Verify validate_python_version recognizes minor version strings and strips whitespace."""
    from scripts.load_db import validate_python_version

    assert validate_python_version("3.10") == "3.10"
    assert validate_python_version("  3.12  ") == "3.12"
    assert validate_python_version("3.8") == "3.8"
    assert validate_python_version(None) is None
    assert validate_python_version("") is None
    assert validate_python_version("3.10.4") == "3.10.4"


async def test_load_documents_in_memory_deduplication(tmp_path: Path):
    """Verify identical records within the same batch are deduplicated in-memory."""
    test_file = tmp_path / "records_with_duplicates.json"
    record = {
        "id": "pep-0634",
        "title": "Pattern Matching",
        "source_url": "https://peps.python.org/pep-0634/",
        "type": "PEP",
        "summary": "Match statement syntax.",
    }
    # Two identical records in the same batch
    records = [record, record.copy()]
    test_file.write_text(json.dumps(records), encoding="utf-8")

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    stats = await load_documents_from_json(test_file, mock_session)

    assert stats.total == 2
    assert stats.inserted == 1
    assert stats.skipped == 1
    assert stats.errors == 0
    # mock_session.get should only be called once because the second was deduplicated in-memory
    assert mock_session.get.await_count == 1
