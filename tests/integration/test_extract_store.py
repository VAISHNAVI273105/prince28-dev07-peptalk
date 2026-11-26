"""Integration tests for pending, extract saving, and metadata persistence against PostgreSQL."""

import pytest
from sqlalchemy import select

from peptalk.config import Settings
from peptalk.db.base import Base
from peptalk.db.models import Document
from peptalk.db.session import make_engine, make_sessionmaker
from peptalk.llm.doc_meta import DocMeta
from peptalk.llm.extract import Extraction, pending, save


@pytest.fixture
async def session(database_url):
    engine = make_engine(Settings(app_env="ci", database_url=database_url, _env_file=None))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as db:
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_pending_and_save_metadata(session):
    doc_id = "test-doc-extract-1"
    # Ensure document does not exist
    existing = await session.scalar(select(Document).where(Document.id == doc_id))
    if existing:
        await session.delete(existing)
        await session.commit()

    doc = Document(
        id=doc_id,
        title="Style Guide for Python Code",
        source_url="https://peps.python.org/pep-0008/",
        sha256="0123456789abcdef" * 4,
        doc_type="PEP",
        document_metadata={"source": "pep-0008.txt", "parser": "text", "chars": 1500},
    )
    session.add(doc)
    await session.commit()

    # 1. pending() finds the new document for version 'v1'
    todo = await pending(session, version="v1")
    assert any(d.id == doc_id for d in todo)

    # 2. save() writes extraction metadata
    record = DocMeta(
        doc_kind="guideline",
        year=2024,
        language="en",
        summary="Style guide for modern clean readable Python programming.",
        topics=["pep8", "style"],
        pep_number=["8"],
        status=["Active"],
        type=["Process"],
        python_version=["3.13"],
        created=["2001-07-05"],
    )
    extraction = Extraction(
        record=record,
        attempts=1,
        errors=[],
        model="gemini-3.5-flash-lite",
        tokens_in=150,
        tokens_out=60,
        cost_inr=0.005,
    )

    await save(session, doc, extraction, version="v1")

    # 3. Reload from DB and verify merged metadata
    refreshed = await session.scalar(select(Document).where(Document.id == doc_id))
    assert refreshed is not None
    meta = refreshed.metadata_

    # Preserved original parser fields
    assert meta["source"] == "pep-0008.txt"
    assert meta["parser"] == "text"
    assert meta["chars"] == 1500

    # Saved extracted fields
    assert meta["doc_kind"] == "guideline"
    assert meta["year"] == 2024
    assert meta["language"] == "en"
    assert meta["pep_number"] == ["8"]

    # Saved extract status note
    assert "extract" in meta
    assert meta["extract"]["prompt"] == "v1"
    assert meta["extract"]["model"] == "gemini-3.5-flash-lite"
    assert meta["extract"]["attempts"] == 1
    assert "error" not in meta["extract"]

    # 4. pending() now excludes this document
    todo_after = await pending(session, version="v1")
    assert not any(d.id == doc_id for d in todo_after)

    # Cleanup
    await session.delete(refreshed)
    await session.commit()
