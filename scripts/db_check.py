"""Safe database connectivity check script for PEPTalk.

Verifies connectivity and executes a ping query against PostgreSQL without
logging or displaying credentials or connection strings.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import text

from peptalk.config import get_settings
from peptalk.db.session import dispose_engine, session_scope

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_check")


async def check_database_connection() -> bool:
    """Verify PostgreSQL connectivity and query server version info safely."""
    settings = get_settings()
    if not settings.database_url:
        logger.error(
            "DATABASE_URL is not configured. Set DATABASE_URL in environment or .env file."
        )
        return False

    try:
        async with session_scope() as session:
            result = await session.execute(
                text("SELECT current_database(), current_user, version();")
            )
            row = result.first()
            if row:
                db_name, db_user, version_str = row
                short_version = version_str.split()[0] if version_str else "PostgreSQL"
                logger.info("Database ping successful (SELECT 1 passed).")
                logger.info("Connected to database: %s", db_name)
                logger.info("Authenticated as user: %s", db_user)
                logger.info("Database engine: %s", short_version)
            return True

    except Exception as exc:
        logger.error("Database connection check failed: %s", type(exc).__name__)
        return False
    finally:
        await dispose_engine()


def main() -> None:
    """CLI entry point."""
    success = asyncio.run(check_database_connection())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
