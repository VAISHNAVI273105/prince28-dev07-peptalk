"""Unit tests for asynchronous PostgreSQL session and engine infrastructure."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from peptalk.config import Settings
from peptalk.db.session import (
    create_async_db_engine,
    create_async_session_factory,
    dispose_engine,
    get_async_engine,
    get_db_session,
    get_session_factory,
    normalize_async_database_url,
    reset_engine,
    session_scope,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _clean_engine_cache():
    """Ensure engine and session factory caches are cleanly reset before and after each test."""
    reset_engine()
    yield
    reset_engine()


# ---------------------------------------------------------------------------
# URL Normalization Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_url", "expected_url"),
    [
        (
            "postgresql://localhost:5432/peptalk",
            "postgresql+asyncpg://localhost:5432/peptalk",
        ),
        (
            "postgres://localhost:5432/peptalk",
            "postgresql+asyncpg://localhost:5432/peptalk",
        ),
        (
            "postgresql+asyncpg://localhost:5432/peptalk",
            "postgresql+asyncpg://localhost:5432/peptalk",
        ),
        (
            "postgresql+psycopg://localhost:5432/peptalk",
            "postgresql+asyncpg://localhost:5432/peptalk",
        ),
        (
            "postgresql+psycopg2://localhost:5432/peptalk",
            "postgresql+asyncpg://localhost:5432/peptalk",
        ),
    ],
)
def test_normalize_supported_schemes(input_url: str, expected_url: str):
    """Verify standard PostgreSQL schemes are normalized to postgresql+asyncpg."""
    assert normalize_async_database_url(input_url) == expected_url


def test_normalize_converts_sslmode_to_ssl_and_preserves_others():
    """Verify sslmode=require is normalized to ssl=require and other parameters preserved."""
    url = "postgresql://localhost:5432/peptalk?sslmode=require&application_name=peptalk"
    normalized = normalize_async_database_url(url)
    assert normalized == (
        "postgresql+asyncpg://localhost:5432/peptalk?ssl=require&application_name=peptalk"
    )


@pytest.mark.parametrize(
    "scheme",
    [
        "postgresql",
        "postgres",
        "postgresql+asyncpg",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    ],
)
def test_normalize_converts_sslmode_across_supported_schemes(scheme: str):
    """Verify sslmode conversion works uniformly across all supported schemes."""
    url = f"{scheme}://localhost:5432/peptalk?sslmode=require"
    expected = "postgresql+asyncpg://localhost:5432/peptalk?ssl=require"
    assert normalize_async_database_url(url) == expected


def test_normalize_existing_ssl_parameter_handled_safely():
    """Verify existing ssl parameter is preserved without duplicate or conflicting params."""
    # When both ssl and sslmode are specified, avoid duplicate ssl parameters
    url_both = "postgresql://localhost:5432/peptalk?ssl=require&sslmode=require"
    assert normalize_async_database_url(url_both) == (
        "postgresql+asyncpg://localhost:5432/peptalk?ssl=require"
    )

    # When only ssl is specified, keep it as is
    url_ssl_only = "postgresql://localhost:5432/peptalk?ssl=require&application_name=peptalk"
    assert normalize_async_database_url(url_ssl_only) == (
        "postgresql+asyncpg://localhost:5432/peptalk?ssl=require&application_name=peptalk"
    )


def test_normalize_removes_unsupported_channel_binding():
    """Verify channel_binding parameter is removed for asyncpg compatibility."""
    url = (
        "postgresql://localhost:5432/peptalk"
        "?sslmode=require&channel_binding=require&application_name=peptalk"
    )
    expected = "postgresql+asyncpg://localhost:5432/peptalk?ssl=require&application_name=peptalk"
    assert normalize_async_database_url(url) == expected


def test_normalize_secret_str_input():
    """Verify SecretStr instances are accepted and properly extracted."""
    secret = SecretStr("postgresql://localhost:5432/peptalk")
    assert normalize_async_database_url(secret) == "postgresql+asyncpg://localhost:5432/peptalk"


def test_normalize_percent_encoded_credentials():
    """Verify percent-encoded characters in connection strings are preserved."""
    raw = "postgresql://u:p%40ss%25w@db/db?sslmode=require"  # pragma: allowlist secret
    expected = "postgresql+asyncpg://u:p%40ss%25w@db/db?ssl=require"  # pragma: allowlist secret
    assert normalize_async_database_url(raw) == expected


@pytest.mark.parametrize("empty_val", [None, "", "   "])
def test_normalize_missing_or_empty_raises_clear_error(empty_val):
    """Verify None or empty connection strings raise a descriptive ValueError."""
    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        normalize_async_database_url(empty_val)


@pytest.mark.parametrize("invalid_url", ["sqlite:///peptalk.db", "mysql://localhost/peptalk"])
def test_normalize_unsupported_scheme_raises_error(invalid_url: str):
    """Verify unsupported schemes raise a clear ValueError with valid options."""
    with pytest.raises(ValueError, match="Unsupported database URL scheme"):
        normalize_async_database_url(invalid_url)


def test_normalize_error_does_not_expose_credentials():
    """Verify exceptions for invalid schemes do not leak connection credentials."""
    secret_url = "mysql://sensitive_user:secret_pass@localhost/db"  # pragma: allowlist secret
    with pytest.raises(ValueError) as exc_info:
        normalize_async_database_url(secret_url)

    error_message = str(exc_info.value)
    assert "sensitive_user" not in error_message
    assert "secret_pass" not in error_message
    assert "Unsupported database URL scheme 'mysql'" in error_message


# ---------------------------------------------------------------------------
# Engine and Session Factory Tests
# ---------------------------------------------------------------------------


async def test_create_async_db_engine_configuration():
    """Verify create_async_db_engine returns a configured AsyncEngine with pre-ping."""
    engine = create_async_db_engine(
        "postgresql://localhost:5432/testdb",
        echo=False,
        pool_pre_ping=True,
    )
    try:
        assert isinstance(engine, AsyncEngine)
        assert engine.url.drivername == "postgresql+asyncpg"
        assert engine.pool._pre_ping is True
    finally:
        await engine.dispose()


async def test_create_async_session_factory_configuration():
    """Verify session factory produces AsyncSession with expire_on_commit=False."""
    engine = create_async_db_engine("postgresql://localhost:5432/testdb")
    try:
        factory = create_async_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)
        assert factory.class_ is AsyncSession
        assert factory.kw["expire_on_commit"] is False
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Lazy Initialization & Disposal Tests
# ---------------------------------------------------------------------------


def test_get_async_engine_missing_configuration_raises_error():
    """Verify lazy engine creation fails fast with clear error when DATABASE_URL is unset."""
    empty_settings = Settings(app_env="local", database_url=None)
    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        get_async_engine(empty_settings)


async def test_get_async_engine_caches_singleton():
    """Verify get_async_engine lazily instantiates and reuses the shared engine."""
    configured_settings = Settings(
        app_env="local",
        database_url=SecretStr("postgresql://localhost:5432/cached_db"),
    )
    engine1 = get_async_engine(configured_settings)
    engine2 = get_async_engine(configured_settings)
    try:
        assert engine1 is engine2
        assert isinstance(engine1, AsyncEngine)
    finally:
        await dispose_engine()


async def test_get_session_factory_with_explicit_engine():
    """Verify get_session_factory can bind an explicit engine without modifying singleton."""
    engine = create_async_db_engine("postgresql://localhost:5432/custom_db")
    try:
        factory = get_session_factory(engine=engine)
        assert factory.kw["bind"] is engine
    finally:
        await engine.dispose()


async def test_dispose_engine_cleans_and_resets():
    """Verify dispose_engine disposes the active connection pool and resets references."""
    configured_settings = Settings(
        app_env="local",
        database_url=SecretStr("postgresql://localhost:5432/dispose_db"),
    )
    engine = get_async_engine(configured_settings)
    factory = get_session_factory()
    assert engine is not None
    assert factory is not None

    await dispose_engine()
    # Calling dispose_engine a second time should be a safe no-op
    await dispose_engine()

    # Next call to get_async_engine should create a new engine instance
    new_engine = get_async_engine(configured_settings)
    try:
        assert new_engine is not engine
    finally:
        await dispose_engine()


# ---------------------------------------------------------------------------
# Session Scope & Dependency Tests (using Mocks)
# ---------------------------------------------------------------------------


def _build_mock_session() -> tuple[AsyncMock, MagicMock]:
    """Build a mock AsyncSession and factory simulating context manager closure."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.__aenter__.return_value = mock_session

    async def _mock_aexit(*args: object) -> None:
        await mock_session.close()

    mock_session.__aexit__.side_effect = _mock_aexit
    mock_factory = MagicMock(return_value=mock_session)
    return mock_session, mock_factory


async def test_session_scope_success_closes_session():
    """Verify session_scope context manager yields session and exits cleanly."""
    mock_session, mock_factory = _build_mock_session()

    async with session_scope(factory=mock_factory) as session:
        assert session is mock_session

    mock_session.__aexit__.assert_awaited_once_with(None, None, None)
    mock_session.close.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


async def test_session_scope_exception_rolls_back_and_closes():
    """Verify session_scope rolls back active transaction on error before closing."""
    mock_session, mock_factory = _build_mock_session()

    with pytest.raises(RuntimeError, match="simulated failure"):
        async with session_scope(factory=mock_factory):
            raise RuntimeError("simulated failure")

    mock_session.rollback.assert_awaited_once()
    mock_session.__aexit__.assert_awaited_once()
    mock_session.close.assert_awaited_once()


async def test_get_db_session_dependency_yields_session(monkeypatch: pytest.MonkeyPatch):
    """Verify FastAPI get_db_session dependency yields session from the factory."""
    mock_session, mock_factory = _build_mock_session()

    monkeypatch.setattr("peptalk.db.session.get_session_factory", lambda: mock_factory)

    gen = get_db_session()
    session = await anext(gen)
    assert session is mock_session

    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    mock_session.__aexit__.assert_awaited_once_with(None, None, None)
    mock_session.close.assert_awaited_once()
