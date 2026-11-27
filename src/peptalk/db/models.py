"""SQLAlchemy models for documents and their pages."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from peptalk.db.base import Base


class Document(Base):
    """A documentation source and its searchable metadata."""

    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "ix_documents_metadata_gin",
            "metadata",
            postgresql_using="gin",
            postgresql_ops={"metadata": "jsonb_path_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    licence: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    external_id = synonym("id")
    metadata_ = synonym("document_metadata")

    pages: Mapped[list[Page]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id!r} title={self.title!r} type={self.doc_type!r}>"

    def __str__(self) -> str:
        return f"{self.id}: {self.title}"


class Page(Base):
    """A page of text belonging to a documentation source."""

    __tablename__ = "pages"
    __table_args__ = (CheckConstraint("page_no > 0", name="ck_pages_page_no_positive"),)

    doc_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id = synonym("doc_id")
    page_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # The section path this page starts in, e.g. ["Fever", "Dengue"]: used for citations.
    headings: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")

    document: Mapped[Document] = relationship(back_populates="pages")

    def __repr__(self) -> str:
        return f"<Page doc_id={self.doc_id!r} page_no={self.page_no}>"

    def __str__(self) -> str:
        return f"{self.doc_id}#p{self.page_no}"


class ParseFailure(Base):
    """The dead-letter table: one row per raw file we could not parse, with the reason."""

    __tablename__ = "parse_failures"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True)  # data/raw/<source>/<file>
    sha256: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(40), index=True)  # no_text_layer, corrupt, ...
    detail: Mapped[str] = mapped_column(Text, server_default="")
    attempts: Mapped[int] = mapped_column(server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LlmCall(Base):
    """One row per call to a language model: who answered, how long, how much."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(String(40), server_default="chat")
    prompt_version: Mapped[str] = mapped_column(String(80), server_default="")
    status: Mapped[str] = mapped_column(String(10))  # ok or error
    error: Mapped[str] = mapped_column(Text, server_default="")
    tokens_in: Mapped[int] = mapped_column(server_default="0")
    tokens_out: Mapped[int] = mapped_column(server_default="0")
    latency_ms: Mapped[int] = mapped_column(server_default="0")
    cost_inr: Mapped[float] = mapped_column(Numeric(12, 6), server_default="0")
    fallback_used: Mapped[bool] = mapped_column(server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class IngestJob(Base):
    """One request to ingest a batch of documents. Its items carry the real work."""

    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requested: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list[IngestItem]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class IngestItem(Base):
    """One document in a batch: queued -> running -> done / skipped / failed."""

    __tablename__ = "ingest_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("ingest_jobs.id", ondelete="CASCADE"), index=True
    )
    record: Mapped[dict[str, Any]] = mapped_column(JSONB)  # the manifest line
    status: Mapped[str] = mapped_column(String(10), server_default="queued", index=True)
    attempts: Mapped[int] = mapped_column(server_default="0")
    error: Mapped[str] = mapped_column(Text, server_default="")
    pages: Mapped[int] = mapped_column(server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped[IngestJob] = relationship(back_populates="items")
