"""Idempotent JSON-to-PostgreSQL document loader for PEPTalk."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.config import get_settings
from peptalk.db.models import Document, Page
from peptalk.db.session import dispose_engine, session_scope

logger = logging.getLogger(__name__)

VALID_PEP_STATUSES: set[str] = {
    "Draft",
    "Active",
    "Accepted",
    "Provisional",
    "Deferred",
    "Rejected",
    "Withdrawn",
    "Final",
    "Superseded",
}


def validate_pep_status(status: str | None) -> str | None:
    """Validate and normalize a PEP status string against standard PEP statuses.

    Returns canonical title-cased status if recognized, otherwise preserves stripped input.
    """
    if not status or not isinstance(status, str):
        return None
    canonical = status.strip().title()
    if canonical in VALID_PEP_STATUSES:
        return canonical
    logger.warning("Unrecognized PEP status encountered: %s", status)
    return status.strip()


PYTHON_VERSION_PATTERN = re.compile(r"^3\.\d+$")


def validate_python_version(version: str | None) -> str | None:
    """Validate and normalize a CPython minor release version string (e.g. '3.10').

    Returns the stripped version string if it matches '3.X', otherwise logs and returns as-is.
    """
    if not version or not isinstance(version, str):
        return None
    cleaned = version.strip()
    if PYTHON_VERSION_PATTERN.match(cleaned):
        return cleaned
    logger.warning("Non-standard Python version string encountered: %s", version)
    return cleaned


@dataclass
class LoadStats:
    """Statistics recorded during document loading."""

    total: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


def compute_canonical_sha256(record: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash from canonical JSON representation.

    Keys are sorted and delimiters are standardized so equivalent JSON objects
    produce identical hashes regardless of whitespace or key ordering.
    """
    canonical_bytes = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def map_record_to_document_and_page(
    record: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map a raw JSON record to Document and Page attribute dictionaries."""
    doc_id = str(record["id"])
    sha256_hash = compute_canonical_sha256(record)

    created_raw = record.get("created")
    published_on = date.fromisoformat(created_raw) if created_raw else None

    # Preserve status, python_version, pep_number, and other source fields in JSONB metadata
    metadata: dict[str, Any] = {}
    for key, value in record.items():
        if key not in {"id", "title", "source_url", "type", "created", "summary"}:
            metadata[key] = value

    if "status" in metadata and isinstance(metadata["status"], str):
        validated_status = validate_pep_status(metadata["status"])
        if validated_status is not None:
            metadata["status"] = validated_status

    if "python_version" in metadata and isinstance(metadata["python_version"], str):
        validated_py = validate_python_version(metadata["python_version"])
        if validated_py is not None:
            metadata["python_version"] = validated_py

    document_attrs: dict[str, Any] = {
        "id": doc_id,
        "title": str(record.get("title", "")),
        "source_url": str(record.get("source_url", "")),
        "licence": record.get("licence"),
        "doc_type": str(record.get("type", "PEP")),
        "published_on": published_on,
        "sha256": sha256_hash,
        "document_metadata": metadata,
    }

    page_attrs: dict[str, Any] = {
        "doc_id": doc_id,
        "page_no": 1,
        "text": str(record.get("summary", "")),
    }

    return document_attrs, page_attrs


async def load_record(session: AsyncSession, record: dict[str, Any]) -> str:
    """Load or update a single document record in the database.

    Returns:
        One of 'inserted', 'updated', or 'skipped'.
    """
    doc_attrs, page_attrs = map_record_to_document_and_page(record)
    doc_id = doc_attrs["id"]
    new_sha256 = doc_attrs["sha256"]

    existing_doc = await session.get(Document, doc_id)

    if existing_doc is None:
        # Insert new Document and Page
        new_doc = Document(**doc_attrs)
        new_page = Page(**page_attrs)
        session.add(new_doc)
        session.add(new_page)
        return "inserted"

    if existing_doc.sha256 == new_sha256:
        # Document content is identical, skip without modification
        return "skipped"

    # Update existing Document fields
    existing_doc.title = doc_attrs["title"]
    existing_doc.source_url = doc_attrs["source_url"]
    existing_doc.licence = doc_attrs["licence"]
    existing_doc.doc_type = doc_attrs["doc_type"]
    existing_doc.published_on = doc_attrs["published_on"]
    existing_doc.sha256 = new_sha256
    existing_doc.document_metadata = doc_attrs["document_metadata"]

    # Update existing Page or insert if missing
    existing_page = await session.get(Page, (doc_id, 1))
    if existing_page is not None:
        existing_page.text = page_attrs["text"]
    else:
        session.add(Page(**page_attrs))

    return "updated"


async def load_documents_from_json(
    file_path: Path | str,
    session: AsyncSession,
    *,
    fail_fast: bool = False,
) -> LoadStats:
    """Load documentation records from a JSON file into PostgreSQL idempotently.

    Args:
        file_path: Path to the JSON source records.
        session: Active async database session.
        fail_fast: If True, raise immediately on the first error. Defaults to False.

    Returns:
        LoadStats detailing the number of inserted, updated, and skipped records.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"JSON source file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        records: list[dict[str, Any]] = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"Expected JSON list in {path}, got {type(records).__name__}")

    stats = LoadStats(total=len(records))

    for record in records:
        if not isinstance(record, dict) or "id" not in record or not record.get("id"):
            stats.errors += 1
            logger.warning("Skipping malformed record missing valid 'id': %s", record)
            if fail_fast:
                raise ValueError("Record is missing required 'id' attribute")
            continue

        try:
            status = await load_record(session, record)
            if status == "inserted":
                stats.inserted += 1
            elif status == "updated":
                stats.updated += 1
            elif status == "skipped":
                stats.skipped += 1
        except Exception:
            stats.errors += 1
            logger.exception("Failed to load record with id '%s'", record.get("id"))
            if fail_fast:
                raise

    await session.commit()
    return stats


async def run_loader(file_path: Path | str) -> LoadStats:
    """Execute the database loader using the application session scope."""
    async with session_scope() as session:
        return await load_documents_from_json(file_path, session)


def main() -> None:
    """CLI entry point for running the loader with uv or python."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Idempotent JSON-to-PostgreSQL document loader for PEPTalk."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=Path("data/sample_records.json"),
        help="Path to JSON records file (default: data/sample_records.json)",
    )

    args = parser.parse_args()

    settings = get_settings()
    if not settings.database_url:
        logger.error(
            "DATABASE_URL is not configured. Set DATABASE_URL in environment or .env file."
        )
        sys.exit(1)

    async def run() -> None:
        try:
            stats = await run_loader(args.file)
            logger.info(
                (
                    "Loading complete from %s: %d total "
                    "(%d inserted, %d updated, %d skipped, %d errors)"
                ),
                args.file,
                stats.total,
                stats.inserted,
                stats.updated,
                stats.skipped,
                stats.errors,
            )
        finally:
            await dispose_engine()

    asyncio.run(run())


if __name__ == "__main__":
    main()
