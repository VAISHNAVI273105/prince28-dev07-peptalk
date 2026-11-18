import os
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from peptalk.db.base import Base
from peptalk.db.models import Document, Page  # noqa: F401

# Resolve project root based on this file's location, not cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = getattr(context, "config", None)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config is not None and config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

SUPPORTED_SCHEMES = {
    "postgresql",
    "postgres",
    "postgresql+asyncpg",
    "postgresql+psycopg",
}


def load_environment(dotenv_path: Path | str | None = None) -> None:
    """Load environment variables from project root .env without overriding existing vars."""
    path = Path(dotenv_path) if dotenv_path is not None else DOTENV_PATH
    load_dotenv(dotenv_path=path, override=False)


def get_sync_database_url(url: str | None = None) -> str:
    """Read and convert DATABASE_URL to synchronous postgresql+psycopg format for Alembic.

    Supports postgresql://, postgres://, postgresql+asyncpg://, and postgresql+psycopg://.
    Preserves all query parameters.
    Raises ValueError if DATABASE_URL is missing or the scheme is unsupported.
    """
    if url is None:
        load_environment()
        url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL environment variable is missing or empty")

    parsed = urlsplit(url)
    if parsed.scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Unsupported database URL scheme '{parsed.scheme}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_SCHEMES))}"
        )

    return urlunsplit(
        ("postgresql+psycopg", parsed.netloc, parsed.path, parsed.query, parsed.fragment)
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_sync_database_url()
    if config is not None:
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    url = get_sync_database_url()
    if config is not None:
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


try:
    is_offline = context.is_offline_mode()
except (AttributeError, NameError):
    is_offline = None

if is_offline is not None:
    if is_offline:
        run_migrations_offline()
    else:
        run_migrations_online()
