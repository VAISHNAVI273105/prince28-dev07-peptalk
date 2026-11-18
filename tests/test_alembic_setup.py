"""Unit tests for Alembic and SQLAlchemy database configuration."""

import os
from pathlib import Path

import pytest
from alembic.config import Config

import migrations.env as migration_env
from migrations.env import get_sync_database_url, load_environment, target_metadata
from peptalk.db.base import Base
from peptalk.db.models import Document, Page


def test_base_metadata_includes_documents_and_pages():
    """Verify Base metadata registers the Document and Page model tables."""
    table_names = set(Base.metadata.tables.keys())
    assert "documents" in table_names
    assert "pages" in table_names
    assert target_metadata is Base.metadata


def test_models_mapped_attributes():
    """Verify Document and Page models have expected mapped columns and relationships."""
    assert hasattr(Document, "id")
    assert hasattr(Document, "title")
    assert hasattr(Document, "pages")
    assert hasattr(Page, "doc_id")
    assert hasattr(Page, "page_no")
    assert hasattr(Page, "document")


def test_project_root_dotenv_path_resolution():
    """Verify DOTENV_PATH is resolved relative to migrations/env.py location, not cwd."""
    expected_root = Path(migration_env.__file__).resolve().parent.parent
    expected_dotenv = expected_root / ".env"

    assert expected_root == migration_env.PROJECT_ROOT
    assert expected_dotenv == migration_env.DOTENV_PATH


def test_project_root_resolution_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Verify project root resolution does not depend on the current working directory."""
    monkeypatch.chdir(tmp_path)
    assert tmp_path != migration_env.PROJECT_ROOT
    assert Path(migration_env.__file__).resolve().parent.parent == migration_env.PROJECT_ROOT


def test_already_set_environment_variable_not_overwritten(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Verify load_environment does not overwrite already-set environment variables."""
    fake_env = tmp_path / ".env"
    fake_env.write_text(
        "DATABASE_URL=postgresql://from_file@localhost:5432/file_db\nCUSTOM_TEST_VAR=from_file\n",
        encoding="utf-8",
    )

    existing_url = "postgresql+asyncpg://existing_user:pass@localhost:5432/existing_db"
    monkeypatch.setenv("DATABASE_URL", existing_url)
    monkeypatch.delenv("CUSTOM_TEST_VAR", raising=False)
    monkeypatch.setattr("migrations.env.DOTENV_PATH", fake_env)

    load_environment(dotenv_path=fake_env)

    assert os.getenv("DATABASE_URL") == existing_url
    assert os.getenv("CUSTOM_TEST_VAR") == "from_file"


def test_database_url_loaded_from_dotenv_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Verify DATABASE_URL is loaded from .env when unset in the process environment."""
    fake_env = tmp_path / ".env"
    fake_env.write_text(
        "DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/test_db?sslmode=require\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("migrations.env.DOTENV_PATH", fake_env)

    converted_url = get_sync_database_url()
    assert converted_url == "postgresql+psycopg://user:pass@localhost:5432/test_db?sslmode=require"


@pytest.mark.parametrize(
    ("input_url", "expected_url"),
    [
        (
            "postgresql://user:pass@localhost:5432/peptalk",
            "postgresql+psycopg://user:pass@localhost:5432/peptalk",
        ),
        (
            "postgres://user:pass@localhost:5432/peptalk",
            "postgresql+psycopg://user:pass@localhost:5432/peptalk",
        ),
        (
            "postgresql+asyncpg://user:pass@localhost:5432/peptalk",
            "postgresql+psycopg://user:pass@localhost:5432/peptalk",
        ),
        (
            "postgresql+psycopg://user:pass@localhost:5432/peptalk",
            "postgresql+psycopg://user:pass@localhost:5432/peptalk",
        ),
    ],
)
def test_url_conversion_supported_formats(input_url: str, expected_url: str):
    """Verify URL conversion produces synchronous postgresql+psycopg format for all schemes."""
    assert get_sync_database_url(input_url) == expected_url


@pytest.mark.parametrize(
    ("input_url", "expected_url"),
    [
        (
            "postgresql+asyncpg://user:pass@db.example.com:5432/peptalk?sslmode=require",
            "postgresql+psycopg://user:pass@db.example.com:5432/peptalk?sslmode=require",
        ),
        (
            "postgres://user:pass@localhost/peptalk?sslmode=require&application_name=peptalk",
            "postgresql+psycopg://user:pass@localhost/peptalk?sslmode=require&application_name=peptalk",
        ),
        (
            "postgresql://user:pass@localhost:5432/peptalk?channel_binding=require",
            "postgresql+psycopg://user:pass@localhost:5432/peptalk?channel_binding=require",
        ),
    ],
)
def test_url_conversion_preserves_query_parameters(input_url: str, expected_url: str):
    """Verify query parameters such as sslmode=require are preserved during conversion."""
    assert get_sync_database_url(input_url) == expected_url


def test_missing_database_url_raises_clear_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Verify missing or empty DATABASE_URL environment variable raises a clear ValueError."""
    fake_dotenv = tmp_path / ".env"
    monkeypatch.setattr("migrations.env.DOTENV_PATH", fake_dotenv)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL environment variable is missing"):
        get_sync_database_url()

    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(ValueError, match="DATABASE_URL environment variable is missing"):
        get_sync_database_url()


def test_unsupported_url_scheme_raises_clear_error():
    """Verify unsupported database URL schemes raise a clear ValueError."""
    with pytest.raises(ValueError, match="Unsupported database URL scheme 'sqlite'"):
        get_sync_database_url("sqlite:///peptalk.db")

    with pytest.raises(ValueError, match="Unsupported database URL scheme 'mysql'"):
        get_sync_database_url("mysql://user:pass@localhost/peptalk")


def test_percent_encoded_credentials_and_config_safety():
    """Verify percent-encoded characters in URL are preserved and handled safely."""
    raw_url = "postgresql+asyncpg://user:p%40ss%25word@db.example.com:5432/peptalk?sslmode=require"
    converted = get_sync_database_url(raw_url)
    expected = "postgresql+psycopg://user:p%40ss%25word@db.example.com:5432/peptalk?sslmode=require"
    assert converted == expected

    # Verify escaping percent signs allows round-trip without interpolation error
    cfg = Config("alembic.ini")
    escaped_url = converted.replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", escaped_url)
    assert cfg.get_main_option("sqlalchemy.url") == converted
