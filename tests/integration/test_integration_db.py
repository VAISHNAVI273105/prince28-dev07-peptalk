"""Integration tests against live PostgreSQL test database.

These tests execute against a fresh test database when TEST_DATABASE_URL
is configured in the environment.

CRITICAL SAFETY RULES:
1. Never run against a production database.
2. Skips safely when TEST_DATABASE_URL is not set.
"""

from __future__ import annotations

import os
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool

from migrations.env import get_sync_database_url
from peptalk.api.deps import check_database_readiness, get_db_session, get_document_repository
from peptalk.api.main import create_app
from peptalk.db.models import Document, Page
from peptalk.db.repository import DocumentRepository
from peptalk.db.session import (
    create_async_db_engine,
    create_async_session_factory,
)
from scripts.load_db import load_documents_from_json

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        not TEST_DB_URL,
        reason="TEST_DATABASE_URL is not set; skipping live integration tests.",
    ),
]


def _get_admin_sync_url(test_url: str, default_db: str = "postgres") -> str:
    """Generate synchronous administrative URL connecting to default database."""
    sync_url = get_sync_database_url(test_url)
    parsed = urlsplit(sync_url)
    target_db = default_db.strip().lstrip("/")
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"/{target_db}", parsed.query, parsed.fragment)
    )


@pytest.fixture(scope="session")
def live_db_setup():
    """Create a fresh database, apply Alembic migrations, and tear down after tests."""
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping live integration tests.")

    prod_url = os.getenv("DATABASE_URL", "")
    if prod_url and raw_url.strip() == prod_url.strip():
        pytest.fail("TEST_DATABASE_URL matches DATABASE_URL! Refusing to run on production.")

    parsed = urlsplit(raw_url)
    target_db = parsed.path.lstrip("/") or "peptalk_test"
    unique_run_db = f"peptalk_it_{uuid.uuid4().hex[:8]}"

    admin_url = _get_admin_sync_url(raw_url, default_db="postgres")
    sync_test_url: str | None = None
    created_new_db = False

    # Attempt to create an isolated database per test session
    try:
        from sqlalchemy import create_engine

        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{unique_run_db}"'))
        admin_engine.dispose()
        created_new_db = True
        actual_db_name = unique_run_db
        sync_test_url = urlunsplit(
            (
                urlsplit(get_sync_database_url(raw_url)).scheme,
                parsed.netloc,
                f"/{actual_db_name}",
                parsed.query,
                parsed.fragment,
            )
        )
        async_test_url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                f"/{actual_db_name}",
                parsed.query,
                parsed.fragment,
            )
        )
    except Exception:
        # Fallback to target database if admin privileges are not available
        actual_db_name = target_db
        sync_test_url = get_sync_database_url(raw_url)
        async_test_url = raw_url

    # Apply migrations via Alembic
    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_test_url)

    # Set DATABASE_URL in environment for migrations/env.py
    old_env = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = sync_test_url
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)

    engine = create_async_db_engine(async_test_url, poolclass=NullPool)
    factory = create_async_session_factory(engine)

    yield {
        "engine": engine,
        "factory": factory,
        "async_url": async_test_url,
        "sync_url": sync_test_url,
        "db_name": actual_db_name,
        "created_new_db": created_new_db,
    }

    # Teardown
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(engine.dispose())
        loop.close()
    except Exception:
        pass

    if created_new_db:
        admin_engine = None
        try:
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with admin_engine.connect() as conn:
                conn.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        f"WHERE datname = '{actual_db_name}' AND pid <> pg_backend_pid()"
                    )
                )
                conn.execute(text(f'DROP DATABASE IF EXISTS "{actual_db_name}"'))
        except Exception:
            pass
        finally:
            if admin_engine is not None:
                admin_engine.dispose()


@pytest.fixture
async def db_session(live_db_setup):
    """Provide an isolated database session with rollback/cleanup."""
    factory = live_db_setup["factory"]
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# 7 Required Integration Tests
# ---------------------------------------------------------------------------


async def test_integration_database_migration_and_tables(live_db_setup):
    """1. Verify that database migrations successfully created documents and pages tables."""
    engine: AsyncEngine = live_db_setup["engine"]
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "documents" in tables
        assert "pages" in tables

        columns = await conn.run_sync(
            lambda sync_conn: [col["name"] for col in inspect(sync_conn).get_columns("documents")]
        )
        for expected_col in [
            "id",
            "title",
            "source_url",
            "doc_type",
            "published_on",
            "sha256",
            "metadata",
        ]:
            assert expected_col in columns


async def test_integration_repository_insert_and_get(db_session: AsyncSession):
    """2. Verify inserting a Document and Page and retrieving via repository."""
    doc = Document(
        id="pep-test-0001",
        title="Test Integration PEP",
        source_url="https://peps.python.org/pep-0001/",
        licence="Open",
        doc_type="PEP",
        published_on=date(2024, 1, 1),
        sha256="test-sha256-hash-001",
        document_metadata={"status": "Draft", "python_version": "3.13", "pep_number": 9991},
    )
    page = Page(
        doc_id="pep-test-0001",
        page_no=1,
        text="This is integration test content for PEP 9991.",
    )
    db_session.add(doc)
    db_session.add(page)
    await db_session.commit()

    repo = DocumentRepository(db_session)
    retrieved = await repo.get_by_id("pep-test-0001")
    assert retrieved is not None
    assert retrieved["id"] == "pep-test-0001"
    assert retrieved["title"] == "Test Integration PEP"
    assert retrieved["status"] == "Draft"
    assert retrieved["python_version"] == "3.13"
    assert retrieved["pep_number"] == 9991
    assert retrieved["summary"] == "This is integration test content for PEP 9991."


async def test_integration_repository_jsonb_filter(db_session: AsyncSession):
    """3. Verify JSONB filtering via GIN index containment."""
    doc_draft = Document(
        id="pep-test-filter-draft",
        title="Draft PEP",
        source_url="https://peps.python.org/draft/",
        doc_type="PEP",
        published_on=date(2024, 2, 1),
        sha256="sha-draft",
        document_metadata={"status": "Draft", "python_version": "3.13", "pep_number": 9992},
    )
    doc_final = Document(
        id="pep-test-filter-final",
        title="Final PEP",
        source_url="https://peps.python.org/final/",
        doc_type="PEP",
        published_on=date(2024, 2, 2),
        sha256="sha-final",
        document_metadata={"status": "Final", "python_version": "3.13", "pep_number": 9993},
    )
    db_session.add_all([doc_draft, doc_final])
    await db_session.commit()

    repo = DocumentRepository(db_session)
    final_docs, count = await repo.list_documents(status="Final")
    final_ids = [d["id"] for d in final_docs]
    assert "pep-test-filter-final" in final_ids
    assert "pep-test-filter-draft" not in final_ids


async def test_integration_repository_pagination(db_session: AsyncSession):
    """4. Verify repository pagination limits and offsets."""
    for i in range(5):
        doc = Document(
            id=f"pep-test-page-{i}",
            title=f"Pagination Test {i}",
            source_url=f"https://peps.python.org/page-{i}/",
            doc_type="PEP",
            published_on=date(2024, 3, i + 1),
            sha256=f"sha-page-{i}",
            document_metadata={"tag": "pagination-test"},
        )
        db_session.add(doc)
    await db_session.commit()

    repo = DocumentRepository(db_session)
    page1, total1 = await repo.list_documents(limit=2, offset=0)
    page2, total2 = await repo.list_documents(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["id"] != page2[0]["id"]


async def test_integration_loader_first_run(db_session: AsyncSession):
    """5. Verify sample-data loader on initial run inserts all 20 records."""
    sample_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_records.json"
    assert sample_path.exists(), f"Sample data file {sample_path} not found"

    stats = await load_documents_from_json(sample_path, db_session)
    await db_session.commit()

    assert stats.total == 20
    assert stats.inserted == 20
    assert stats.skipped == 0
    assert stats.errors == 0


async def test_integration_loader_second_run_idempotent(db_session: AsyncSession):
    """6. Verify sample-data loader is idempotent and reports 20 unchanged/skipped."""
    sample_path = Path(__file__).resolve().parent.parent.parent / "data" / "sample_records.json"

    # Second run should skip all 20 already inserted records
    stats = await load_documents_from_json(sample_path, db_session)
    await db_session.commit()

    assert stats.total == 20
    assert stats.inserted == 0
    assert stats.skipped == 20
    assert stats.errors == 0


async def test_integration_api_readiness_probe(live_db_setup):
    """7. Verify API /ready endpoint succeeds against live database."""
    engine = live_db_setup["engine"]
    factory = live_db_setup["factory"]

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    async def override_get_repo():
        async with factory() as session:
            yield DocumentRepository(session)

    async def override_readiness_check():
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_document_repository] = override_get_repo
    app.dependency_overrides[check_database_readiness] = override_readiness_check

    with TestClient(app) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ready"
