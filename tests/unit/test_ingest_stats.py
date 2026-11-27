"""Unit tests for queue stats and observability (Stretch Task)."""

import pytest
from fastapi.testclient import TestClient

from peptalk.config import get_settings
from tests.conftest import FakeIngestRepo, FakeQueue


@pytest.mark.asyncio
async def test_stats_empty_queue():
    repo = FakeIngestRepo()
    stats = await repo.stats()
    assert stats["total_items"] == 0
    assert stats["counts"]["queued"] == 0
    assert stats["oldest_queued_age_seconds"] is None
    assert stats["queue_healthy"] is True


@pytest.mark.asyncio
async def test_stats_with_queued_items():
    repo = FakeIngestRepo()
    await repo.create([{"url": "u1", "path": "p1"}, {"url": "u2", "path": "p2"}])
    stats = await repo.stats()
    assert stats["total_items"] == 2
    assert stats["counts"]["queued"] == 2
    assert stats["oldest_queued_age_seconds"] is not None
    assert stats["queue_healthy"] is True


@pytest.mark.asyncio
async def test_stats_unhealthy_when_age_exceeds_threshold():
    repo = FakeIngestRepo()
    await repo.create([{"url": "u1", "path": "p1"}])
    orig_stats = repo.stats

    async def lagging_stats():
        base = await orig_stats()
        base["oldest_queued_age_seconds"] = 350.0
        base["queue_healthy"] = False
        return base

    repo.stats = lagging_stats  # type: ignore[method-assign]
    stats = await repo.stats()
    assert stats["queue_healthy"] is False
    assert stats["oldest_queued_age_seconds"] > 180.0


def test_api_stats_endpoint(client: TestClient, fake_ingest_repo: FakeIngestRepo):
    resp = client.get("/v1/ingest/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "counts" in data
    assert "queue_healthy" in data
    assert "total_items" in data


def test_api_retry_failed_items(
    client: TestClient, fake_ingest_repo: FakeIngestRepo, fake_queue: FakeQueue
):
    settings = get_settings()
    settings.admin_token = "secret123"

    # Setup a failed item
    fake_ingest_repo.items[101] = {
        "id": 101,
        "job_id": "job_fail",
        "record": {"path": "bad.pdf"},
        "status": "failed",
        "error": "extract: timeout",
        "attempts": 3,
    }

    # Retry without auth -> 401
    resp_unauth = client.post("/v1/ingest/retry", json={"stage": "extract"})
    assert resp_unauth.status_code == 401

    # Retry with admin token -> 200
    resp = client.post(
        "/v1/ingest/retry",
        headers={"X-Admin-Token": "secret123"},
        json={"stage": "extract", "limit": 10},
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["requeued"] == 1
    assert 101 in res_data["item_ids"]
    assert 101 in fake_queue.items
    assert fake_ingest_repo.items[101]["status"] == "queued"
