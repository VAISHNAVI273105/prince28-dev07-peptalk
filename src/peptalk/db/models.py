"""SQLAlchemy models for documents and their pages."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    page_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped[Document] = relationship(back_populates="pages")

    def __repr__(self) -> str:
        return f"<Page doc_id={self.doc_id!r} page_no={self.page_no}>"

    def __str__(self) -> str:
        return f"{self.doc_id}#p{self.page_no}"
