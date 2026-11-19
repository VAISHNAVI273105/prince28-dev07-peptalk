"""Unit tests for utility scripts (db_check and explain)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.db_check import check_database_connection
from scripts.explain import explain_query

pytestmark = pytest.mark.anyio


async def test_db_check_missing_url(monkeypatch: pytest.MonkeyPatch):
    """Verify db_check returns False when DATABASE_URL is unset."""
    monkeypatch.setattr(
        "scripts.db_check.get_settings",
        lambda: MagicMock(database_url=None),
    )
    result = await check_database_connection()
    assert result is False


async def test_db_check_success(monkeypatch: pytest.MonkeyPatch):
    """Verify db_check queries server info and returns True on success."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = ("testdb", "testuser", "PostgreSQL 16.0")
    mock_session.execute.return_value = mock_result

    mock_scope = MagicMock()
    mock_scope.__aenter__.return_value = mock_session
    mock_scope.__aexit__.return_value = None

    monkeypatch.setattr(
        "scripts.db_check.get_settings",
        lambda: MagicMock(database_url="postgresql://localhost/testdb"),
    )
    monkeypatch.setattr("scripts.db_check.session_scope", lambda: mock_scope)
    monkeypatch.setattr("scripts.db_check.dispose_engine", AsyncMock())

    result = await check_database_connection()
    assert result is True
    mock_session.execute.assert_awaited_once()


async def test_db_check_connection_failure(monkeypatch: pytest.MonkeyPatch):
    """Verify db_check returns False and logs error when connection fails."""
    mock_scope = MagicMock()
    mock_scope.__aenter__.side_effect = ConnectionRefusedError("Connection failed")
    mock_scope.__aexit__.return_value = None

    monkeypatch.setattr(
        "scripts.db_check.get_settings",
        lambda: MagicMock(database_url="postgresql://localhost/testdb"),
    )
    monkeypatch.setattr("scripts.db_check.session_scope", lambda: mock_scope)
    monkeypatch.setattr("scripts.db_check.dispose_engine", AsyncMock())

    result = await check_database_connection()
    assert result is False


async def test_explain_missing_url(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture):
    """Verify explain_query logs error and exits early when DATABASE_URL is unset."""
    monkeypatch.setattr(
        "scripts.explain.get_settings",
        lambda: MagicMock(database_url=None),
    )
    await explain_query('{"python_version": "3.10"}')
    captured = capsys.readouterr()
    assert "EXPLAIN ANALYSIS" not in captured.out


async def test_explain_query_execution(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    """Verify explain_query executes default and forced-index explain plans."""
    mock_session = AsyncMock()
    mock_result_default = MagicMock()
    mock_result_default.fetchall.return_value = [("Seq Scan on documents  (cost=0.00..1.25)",)]
    mock_result_forced = MagicMock()
    mock_result_forced.fetchall.return_value = [
        ("Bitmap Heap Scan on documents  (cost=8.00..12.00)",),
        ("  ->  Bitmap Index Scan on ix_documents_metadata_gin",),
    ]

    mock_session.execute.side_effect = [
        mock_result_default,  # Plan 1 default
        None,  # SET LOCAL enable_seqscan = off
        mock_result_forced,  # Plan 2 forced
    ]

    mock_scope = MagicMock()
    mock_scope.__aenter__.return_value = mock_session
    mock_scope.__aexit__.return_value = None

    monkeypatch.setattr(
        "scripts.explain.get_settings",
        lambda: MagicMock(database_url="postgresql://localhost/testdb"),
    )
    monkeypatch.setattr("scripts.explain.session_scope", lambda: mock_scope)

    await explain_query('{"python_version": "3.10"}')
    captured = capsys.readouterr()

    assert "EXPLAIN ANALYSIS: JSONB CONTAINMENT QUERY" in captured.out
    assert "DEFAULT QUERY PLAN" in captured.out
    assert "FORCED INDEX SCAN DEMONSTRATION" in captured.out
    assert "Bitmap Index Scan on ix_documents_metadata_gin" in captured.out
    assert mock_session.execute.await_count == 3
