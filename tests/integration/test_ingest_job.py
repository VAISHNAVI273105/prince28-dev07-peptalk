"""Integration tests for IngestRepository against PostgreSQL."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.config import Settings
from peptalk.db.base import Base
from peptalk.db.ingest_jobs import IngestRepository
from peptalk.db.models import Document, IngestItem, IngestJob
from peptalk.db.session import make_engine, make_sessionmaker


@pytest.fixture
async def db_session(database_url: str):
    """Yield an isolated test session; skip if TEST_DATABASE_URL is not set."""
    engine = make_engine(Settings(app_env="ci", database_url=database_url, _env_file=None))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def repo(db_session: AsyncSession) -> IngestRepository:
    return IngestRepository(db_session)


@pytest.mark.asyncio
async def test_create_and_progress(repo: IngestRepository):
    records = [
        {"url": "http://example.com/1", "path": "p1"},
        {"url": "http://example.com/2", "path": "p2"},
    ]
    job_id, item_ids = await repo.create(records)
    assert len(item_ids) == 2

    progress = await repo.progress(job_id)
    assert progress is not None
    assert progress["job_id"] == job_id
    assert progress["requested"] == 2
    assert progress["queued"] == 2
    assert progress["done"] == 0


@pytest.mark.asyncio
async def test_progress_unknown_job_returns_none(repo: IngestRepository):
    assert await repo.progress("nonexistent_job_id") is None


@pytest.mark.asyncio
async def test_known_ids(repo: IngestRepository, db_session: AsyncSession):
    doc = Document(
        id="test-doc-id-123",
        source_url="http://example.com/doc",
        sha256="0" * 64,
        title="Test Doc",
        doc_type="pep",
        document_metadata={},
    )
    db_session.add(doc)
    await db_session.commit()

    known = await repo.known_ids()
    assert "test-doc-id-123" in known


@pytest.mark.asyncio
async def test_dead_letter_and_failed_records(repo: IngestRepository, db_session: AsyncSession):
    job = IngestJob(id="job_fail_test", requested=1)
    db_session.add(job)
    item = IngestItem(
        job_id="job_fail_test",
        record={"path": "bad.pdf"},
        status="failed",
        error="parse: corrupt",
        attempts=3,
    )
    db_session.add(item)
    await db_session.commit()

    dead = await repo.dead_letter(limit=10)
    assert any(d["path"] == "bad.pdf" and "corrupt" in d["error"] for d in dead)

    failed = await repo.failed_records()
    assert any(r.get("path") == "bad.pdf" for r in failed)
