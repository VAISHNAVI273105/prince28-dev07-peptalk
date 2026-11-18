from sqlalchemy import CheckConstraint, String, Text, inspect
from sqlalchemy.dialects.postgresql import JSONB

from peptalk.db import Base, Document, Page


def test_document_table_and_required_columns():
    table = Document.__table__

    assert table.name == "documents"
    assert set(table.columns) == {
        table.c.id,
        table.c.title,
        table.c.source_url,
        table.c.licence,
        table.c.doc_type,
        table.c.published_on,
        table.c.sha256,
        table.c.metadata,
    }
    assert isinstance(table.c.id.type, String)
    assert table.c.id.primary_key
    assert not table.c.title.nullable
    assert isinstance(table.c.source_url.type, Text)
    assert not table.c.source_url.nullable
    assert table.c.licence.nullable
    assert not table.c.doc_type.nullable
    assert table.c.published_on.nullable
    assert table.c.sha256.type.length == 64
    assert not table.c.sha256.nullable
    assert Base.metadata is Document.metadata


def test_document_metadata_uses_postgresql_jsonb_and_database_name():
    column = Document.__table__.c.metadata

    assert column.name == "metadata"
    assert isinstance(column.type, JSONB)
    assert not column.nullable
    assert column.default is not None
    assert column.default.arg(None) == {}
    assert column.server_default is not None


def test_page_table_columns_and_composite_primary_key():
    table = Page.__table__

    assert table.name == "pages"
    assert set(table.columns) == {table.c.doc_id, table.c.page_no, table.c.text}
    assert isinstance(table.c.doc_id.type, String)
    assert isinstance(table.c.text.type, Text)
    assert not table.c.text.nullable
    assert {column.name for column in table.primary_key.columns} == {"doc_id", "page_no"}


def test_page_document_foreign_key_cascades_on_delete():
    foreign_key = next(iter(Page.__table__.c.doc_id.foreign_keys))

    assert foreign_key.target_fullname == "documents.id"
    assert foreign_key.ondelete == "CASCADE"


def test_page_number_must_be_positive():
    constraint = next(
        constraint
        for constraint in Page.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    )

    assert constraint.name == "ck_pages_page_no_positive"
    assert str(constraint.sqltext) == "page_no > 0"


def test_document_and_page_relationships_have_delete_cascade_behavior():
    document_pages = inspect(Document).relationships["pages"]
    page_document = inspect(Page).relationships["document"]

    assert document_pages.mapper.class_ is Page
    assert document_pages.back_populates == "document"
    assert "delete-orphan" in document_pages.cascade
    assert document_pages.passive_deletes
    assert page_document.mapper.class_ is Document
    assert page_document.back_populates == "pages"
