"""Unit tests for /v1/ingest endpoints."""

from fastapi import HTTPException
from fastapi.testclient import TestClient

from peptalk.api.deps import get_manifest, get_queue
from peptalk.config import get_settings


def test_ingest_start_accepted_returns_202(client: TestClient):
    settings = get_settings()
    settings.admin_token = "secret123"

    response = client.post(
        "/v1/ingest",
        json={"limit": 10},
        headers={"X-Admin-Token": "secret123"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["queued"] == 2
    assert f"/v1/ingest/{data['job_id']}" in data["status_url"]


def test_ingest_start_missing_admin_token_returns_401(client: TestClient):
    settings = get_settings()
    settings.admin_token = "secret123"

    response = client.post("/v1/ingest", json={"limit": 10})
    assert response.status_code == 401
    assert "Missing or wrong X-Admin-Token" in response.json()["detail"]


def test_ingest_start_wrong_admin_token_returns_401(client: TestClient):
    settings = get_settings()
    settings.admin_token = "secret123"

    response = client.post(
        "/v1/ingest",
        json={"limit": 10},
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert response.status_code == 401
    assert "Missing or wrong X-Admin-Token" in response.json()["detail"]


def test_ingest_start_admin_token_unset_returns_403(client: TestClient):
    settings = get_settings()
    settings.admin_token = ""

    response = client.post(
        "/v1/ingest",
        json={"limit": 10},
        headers={"X-Admin-Token": "any-token"},
    )
    assert response.status_code == 403
    assert "Set ADMIN_TOKEN" in response.json()["detail"]


def test_ingest_start_nothing_to_do_returns_200(client: TestClient):
    settings = get_settings()
    settings.admin_token = "secret123"

    def empty_manifest() -> list:
        return []

    client.app.dependency_overrides[get_manifest] = empty_manifest

    response = client.post(
        "/v1/ingest",
        json={"limit": 10},
        headers={"X-Admin-Token": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] is None
    assert data["queued"] == 0
    assert "Nothing to do" in data["detail"]


def test_ingest_progress_success_returns_200(client: TestClient):
    settings = get_settings()
    settings.admin_token = "secret123"

    # Start a job first
    start_resp = client.post(
        "/v1/ingest",
        json={"limit": 10},
        headers={"X-Admin-Token": "secret123"},
    )
    job_id = start_resp.json()["job_id"]

    progress_resp = client.get(f"/v1/ingest/{job_id}")
    assert progress_resp.status_code == 200
    data = progress_resp.json()
    assert data["job_id"] == job_id
    assert data["requested"] == 2
    assert data["queued"] == 2


def test_ingest_progress_not_found_returns_404(client: TestClient):
    response = client.get("/v1/ingest/nonexistent_job_id")
    assert response.status_code == 404
    assert "No ingest job" in response.json()["detail"]


def test_ingest_dead_letter_returns_list(client: TestClient):
    response = client.get("/v1/ingest/dead-letter")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_ingest_redis_down_returns_503(client: TestClient):
    settings = get_settings()
    settings.admin_token = "secret123"

    async def broken_queue():
        raise HTTPException(status_code=503, detail="The job queue (Redis) cannot be reached.")

    client.app.dependency_overrides[get_queue] = broken_queue

    response = client.post(
        "/v1/ingest",
        json={"limit": 10},
        headers={"X-Admin-Token": "secret123"},
    )
    assert response.status_code == 503
    assert "The job queue (Redis) cannot be reached." in response.json()["detail"]
