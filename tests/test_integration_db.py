"""Optional integration tests against a live PostgreSQL test database.

These tests are skipped by default and only execute when TEST_DATABASE_URL
is explicitly configured in the process environment.

CRITICAL SAFETY RULE:
Never configure TEST_DATABASE_URL with a production database connection string.
"""

import os

import pytest
from sqlalchemy import select, text

from peptalk.db.models import Document
from peptalk.db.session import (
    create_async_db_engine,
    create_async_session_factory,
)

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        not TEST_DB_URL,
        reason="TEST_DATABASE_URL is not set; skipping live integration tests.",
    ),
]


@pytest.fixture
def test_engine():
    """Create engine for integration testing and ensure disposal."""
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not configured")

    prod_url = os.getenv("DATABASE_URL", "")
    if prod_url and TEST_DB_URL.strip() == prod_url.strip():
        pytest.fail("TEST_DATABASE_URL matches DATABASE_URL! Refusing to run on production.")

    engine = create_async_db_engine(TEST_DB_URL)
    yield engine
    # Cleanup handled by caller


async def test_live_database_ping(test_engine):
    """Verify live test database connection and ping query."""
    async with test_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await test_engine.dispose()


async def test_live_gin_index_containment_query(test_engine):
    """Verify JSONB containment query functions on live PostgreSQL with GIN index."""
    factory = create_async_session_factory(test_engine)
    async with factory() as session:
        # Query using the exact GIN containment operator (@>)
        stmt = select(Document).where(Document.document_metadata.contains({"status": "Final"}))
        result = await session.execute(stmt)
        # Verify query executes without syntax or type errors on live PostgreSQL
        assert result is not None
    await test_engine.dispose()
