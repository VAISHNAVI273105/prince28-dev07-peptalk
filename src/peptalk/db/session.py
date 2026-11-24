"""Asynchronous PostgreSQL session and engine infrastructure for PEPTalk."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from peptalk.config import Settings, get_settings

logger = logging.getLogger(__name__)

SUPPORTED_SCHEMES = {
    "postgresql",
    "postgres",
    "postgresql+asyncpg",
    "postgresql+psycopg",
    "postgresql+psycopg2",
}

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_async_database_url(url: str | SecretStr | None) -> str:
    """Normalize a PostgreSQL connection string to the postgresql+asyncpg dialect.

    Supports standard postgresql://, postgres://, postgresql+asyncpg://, and
    postgresql+psycopg:// schemes. Converts sslmode to ssl for asyncpg while
    preserving credentials, network locations, paths, and unrelated query parameters.

    Credentials are never exposed in exceptions or logs.

    Args:
        url: Database URL as a plain string or SecretStr.

    Returns:
        Normalized connection URL with the postgresql+asyncpg scheme.

    Raises:
        ValueError: If url is None, blank, or uses an unsupported scheme.
    """
    if url is None:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Set DATABASE_URL in environment or application settings."
        )

    raw_url = url.get_secret_value() if isinstance(url, SecretStr) else str(url)
    if not raw_url.strip():
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Set DATABASE_URL in environment or application settings."
        )

    parsed = urlsplit(raw_url)
    if parsed.scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Unsupported database URL scheme '{parsed.scheme}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_SCHEMES))}"
        )

    query = parsed.query
    if query:
        pairs = parse_qsl(query, keep_blank_values=True)
        has_ssl = any(k == "ssl" for k, _ in pairs)
        normalized_pairs: list[tuple[str, str]] = []
        for k, v in pairs:
            if k == "channel_binding":
                continue
            elif k == "sslmode":
                if not has_ssl:
                    normalized_pairs.append(("ssl", v))
                    has_ssl = True
            else:
                normalized_pairs.append((k, v))
        query = urlencode(normalized_pairs, quote_via=quote)

    return urlunsplit(("postgresql+asyncpg", parsed.netloc, parsed.path, query, parsed.fragment))


def create_async_db_engine(
    url: str | SecretStr,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
    pool_recycle: int = 1800,
    **kwargs: Any,
) -> AsyncEngine:
    """Create an asynchronous SQLAlchemy engine for PostgreSQL.

    Args:
        url: Database connection string or SecretStr.
        echo: Whether to log generated SQL statements.
        pool_pre_ping: Pre-ping connections before checkout (essential for Neon).
        pool_recycle: Seconds after which idle connections are recycled (default 1800).
        **kwargs: Additional keyword arguments forwarded to create_async_engine.

    Returns:
        A configured AsyncEngine instance.
    """
    normalized_url = normalize_async_database_url(url)
    return create_async_engine(
        normalized_url,
        echo=echo,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        **kwargs,
    )


def create_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async_sessionmaker configured with expire_on_commit=False.

    Args:
        engine: Bound AsyncEngine instance.

    Returns:
        Configured async_sessionmaker producing AsyncSession instances.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_async_engine(settings: Settings | None = None) -> AsyncEngine:
    """Retrieve or lazily initialize the shared asynchronous SQLAlchemy engine.

    Args:
        settings: Optional Settings instance. Defaults to get_settings().

    Returns:
        Shared AsyncEngine instance.

    Raises:
        ValueError: If DATABASE_URL is not configured.
    """
    global _engine
    if _engine is None:
        resolved_settings = settings if settings is not None else get_settings()
        if not resolved_settings.database_url:
            raise ValueError(
                "DATABASE_URL is not configured. "
                "Set DATABASE_URL in environment or application settings."
            )
        _engine = create_async_db_engine(resolved_settings.database_url)
    return _engine


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Retrieve or lazily initialize the shared async_sessionmaker.

    Args:
        engine: Optional AsyncEngine to bind. If None, uses get_async_engine().

    Returns:
        Configured async_sessionmaker.
    """
    global _session_factory
    if engine is not None:
        return create_async_session_factory(engine)

    if _session_factory is None:
        active_engine = get_async_engine()
        _session_factory = create_async_session_factory(active_engine)
    return _session_factory


async def dispose_engine() -> None:
    """Dispose of the shared engine connection pool and reset global references."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None


def reset_engine() -> None:
    """Reset cached engine and session factory references without awaiting disposal."""
    global _engine, _session_factory
    if _engine is not None:
        with suppress(Exception):
            _engine.sync_engine.dispose()
    _engine = None
    _session_factory = None


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Asynchronous context manager providing an AsyncSession with automatic cleanup.

    Rolls back active transactions on unhandled exceptions and closes the session
    upon context exit.

    Args:
        factory: Optional async_sessionmaker. Defaults to get_session_factory().

    Yields:
        Active AsyncSession instance.
    """
    active_factory = factory if factory is not None else get_session_factory()
    async with active_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession with proper cleanup and disposal.

    Yields:
        Active AsyncSession instance.
    """
    async with session_scope() as session:
        yield session


def make_engine(
    settings_or_url: Settings | str | SecretStr | None = None, **kwargs: Any
) -> AsyncEngine:
    """Convenience alias for create_async_db_engine accepting Settings or URL."""
    url = settings_or_url.database_url if isinstance(settings_or_url, Settings) else settings_or_url
    return create_async_db_engine(url, **kwargs)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Convenience alias for create_async_session_factory."""
    return create_async_session_factory(engine)
