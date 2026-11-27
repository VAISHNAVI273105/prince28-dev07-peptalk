import os
import secrets
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Ensure safe default environment for tests in clean clones / CI
os.environ.setdefault("APP_ENV", "ci")

from peptalk.api.deps import (
    check_database_readiness,
    get_document_repository,
    get_ingest_repository,
    get_manifest,
    get_queue,
    get_usage_repository,
)
from peptalk.api.main import create_app
from peptalk.db.repository import DocumentStoreAdapter
from peptalk.llm.gateway import FakeLLM, LLMGateway
from peptalk.store import DocumentStore


class FakeUsageRepo:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []

    async def by_day(self, days: int = 7) -> list[dict[str, Any]]:
        return self.rows

    async def latency_percentiles(self, days: int = 7) -> dict[str, Any]:
        return {
            "count": 1,
            "min_ms": 1200,
            "max_ms": 1200,
            "p50_ms": 1200.0,
            "p90_ms": 1200.0,
            "p95_ms": 1200.0,
            "p99_ms": 1200.0,
            "meets_p95_target": True,
        }


class FakeQueue:
    def __init__(self) -> None:
        self.items: list[int] = []

    async def put(self, item_ids: list[int]) -> None:
        self.items.extend(item_ids)


class FakeIngestRepo:
    def __init__(self, known: set[str] | None = None) -> None:
        self._known = known or set()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.items: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    async def known_ids(self) -> set[str]:
        return set(self._known)

    async def create(self, records: list[dict[str, Any]]) -> tuple[str, list[int]]:
        job_id = secrets.token_hex(16)
        item_ids = []
        for r in records:
            item_id = self._next_id
            self._next_id += 1
            self.items[item_id] = {
                "id": item_id,
                "job_id": job_id,
                "record": r,
                "status": "queued",
                "attempts": 0,
                "error": "",
                "pages": 0,
            }
            item_ids.append(item_id)
        self.jobs[job_id] = {
            "job_id": job_id,
            "requested": len(records),
            "items": item_ids,
        }
        return job_id, item_ids

    async def progress(self, job_id: str) -> dict[str, Any] | None:
        if job_id not in self.jobs:
            return None
        job = self.jobs[job_id]
        counts = {
            "queued": 0,
            "running": 0,
            "done": 0,
            "skipped": 0,
            "failed": 0,
            "pages": 0,
        }
        for iid in job["items"]:
            it = self.items[iid]
            st = it["status"]
            counts[st] = counts.get(st, 0) + 1
            counts["pages"] += it.get("pages", 0)
        return {
            "job_id": job_id,
            "requested": job["requested"],
            **counts,
        }

    async def dead_letter(self, limit: int = 100) -> list[dict[str, Any]]:
        failed = [it for it in self.items.values() if it["status"] == "failed"]
        return failed[:limit]

    async def failed_records(self) -> list[dict[str, Any]]:
        return [it["record"] for it in self.items.values() if it["status"] == "failed"]


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM("fake", "fake-model", ["PEPTalk answers Python questions accurately."])


@pytest.fixture
def llm(fake_llm: FakeLLM) -> LLMGateway:
    return LLMGateway([fake_llm], usd_inr=95.0)


@pytest.fixture
def fake_usage_repo() -> FakeUsageRepo:
    return FakeUsageRepo(
        [
            {
                "date": "2026-11-25",
                "calls": 1,
                "tokens_in": 120,
                "tokens_out": 45,
                "cost_inr": 0.035,
                "fallbacks": 0,
                "errors": 0,
            }
        ]
    )


@pytest.fixture
def fake_queue() -> FakeQueue:
    return FakeQueue()


@pytest.fixture
def fake_ingest_repo() -> FakeIngestRepo:
    return FakeIngestRepo()


@pytest.fixture
def sample_manifest() -> list[dict[str, Any]]:
    return [
        {
            "url": "https://github.com/python/peps/blob/main/peps/pep-0634.rst",
            "source": "pep",
            "path": "data/raw/pep/pep-0634.rst",
            "sha256": "3b2c89b3" * 8,
            "status": "downloaded",
            "via": "git",
            "commit": "3b2c89b3",
        },
        {
            "url": "https://github.com/python/peps/blob/main/peps/pep-0635.rst",
            "source": "pep",
            "path": "data/raw/pep/pep-0635.rst",
            "sha256": "4c3d90c4" * 8,
            "status": "downloaded",
            "via": "git",
            "commit": "4c3d90c4",
        },
    ]


@pytest.fixture
def client(
    llm: LLMGateway,
    fake_usage_repo: FakeUsageRepo,
    fake_queue: FakeQueue,
    fake_ingest_repo: FakeIngestRepo,
    sample_manifest: list[dict[str, Any]],
):
    app = create_app()
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    app.dependency_overrides[get_document_repository] = lambda: adapter
    app.dependency_overrides[check_database_readiness] = lambda: True
    app.dependency_overrides[get_usage_repository] = lambda: fake_usage_repo
    app.dependency_overrides[get_ingest_repository] = lambda: fake_ingest_repo
    app.dependency_overrides[get_queue] = lambda: fake_queue
    app.dependency_overrides[get_manifest] = lambda: sample_manifest
    app.state.gateway = llm

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def database_url():
    """Integration test database connection URL. Skips if TEST_DATABASE_URL is not set."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping live integration tests.")
    return url
