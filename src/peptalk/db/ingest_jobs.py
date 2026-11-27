"""Database queries for ingest jobs and items."""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from peptalk.db.models import Document, IngestItem, IngestJob


class IngestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def known_ids(self) -> set[str]:
        """All external IDs already present in the documents table."""
        stmt = select(Document.external_id)
        return set(await self.session.scalars(stmt))

    async def create(self, records: list[dict[str, Any]]) -> tuple[str, list[int]]:
        """Create an IngestJob and IngestItem rows for a batch of records."""
        job_id = secrets.token_hex(16)
        job = IngestJob(id=job_id, requested=len(records))
        self.session.add(job)
        items = [IngestItem(job_id=job_id, record=record, status="queued") for record in records]
        self.session.add_all(items)
        await self.session.flush()
        await self.session.commit()
        return job_id, [item.id for item in items]

    async def progress(self, job_id: str) -> dict[str, Any] | None:
        """Counts by status for a given job."""
        job = await self.session.get(IngestJob, job_id)
        if job is None:
            return None
        stmt = (
            select(IngestItem.status, func.count(IngestItem.id), func.sum(IngestItem.pages))
            .where(IngestItem.job_id == job_id)
            .group_by(IngestItem.status)
        )
        rows = (await self.session.execute(stmt)).all()
        counts: dict[str, int] = {
            "queued": 0,
            "running": 0,
            "done": 0,
            "skipped": 0,
            "failed": 0,
            "pages": 0,
        }
        for status, count, pages in rows:
            if status in counts:
                counts[status] = count
            if pages:
                counts["pages"] += int(pages)
        return {
            "job_id": job_id,
            "requested": job.requested,
            **counts,
        }

    async def dead_letter(self, limit: int = 100) -> list[dict[str, Any]]:
        """Items that failed permanently."""
        stmt = (
            select(IngestItem)
            .where(IngestItem.status == "failed")
            .order_by(IngestItem.updated_at.desc())
            .limit(limit)
        )
        items = list(await self.session.scalars(stmt))
        return [
            {
                "id": item.id,
                "job_id": item.job_id,
                "path": item.record.get("path", ""),
                "error": item.error,
                "attempts": item.attempts,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in items
        ]

    async def failed_records(self) -> list[dict[str, Any]]:
        """Distinct records that failed, ready for retry."""
        stmt = (
            select(IngestItem.record).where(IngestItem.status == "failed").order_by(IngestItem.id)
        )
        return list(await self.session.scalars(stmt))
