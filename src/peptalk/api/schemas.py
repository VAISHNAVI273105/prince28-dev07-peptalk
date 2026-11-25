"""Pydantic schemas for PEPTalk API request and response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Schema representing an individual Python documentation record."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Unique document identifier (e.g. 'pep-0634').")
    title: str = Field(description="Title of the document.")
    type: str = Field(default="PEP", description="Type of document (e.g. 'PEP' or 'What's New').")
    source_url: str = Field(description="Canonical upstream source URL.")
    created: str | None = Field(default=None, description="ISO publication date.")
    licence: str | None = Field(default=None, description="Documentation license.")
    summary: str | None = Field(default=None, description="First-page text summary.")


class DocumentListResponse(BaseModel):
    """Paginated collection of documentation records."""

    total: int = Field(ge=0, description="Total matching documents across all pages.")
    limit: int = Field(ge=1, le=100, description="Maximum items requested.")
    offset: int = Field(ge=0, description="Number of items skipped from start.")
    items: list[DocumentResponse] = Field(description="List of documentation items.")


class PageResponse(BaseModel):
    """Schema representing an individual page of a document with citation section paths."""

    model_config = ConfigDict(extra="allow")

    document_id: str = Field(description="Parent document identifier.")
    page_no: int = Field(ge=1, description="1-indexed sequence page number.")
    text: str = Field(description="Clean text content of the page.")
    headings: list[str] = Field(
        default_factory=list, description="Section hierarchy path active at page start."
    )
