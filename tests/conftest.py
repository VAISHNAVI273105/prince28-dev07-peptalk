import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Ensure safe default environment for tests in clean clones / CI
os.environ.setdefault("APP_ENV", "ci")

from peptalk.api.deps import (
    check_database_readiness,
    get_document_repository,
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
def client(llm: LLMGateway, fake_usage_repo: FakeUsageRepo):
    app = create_app()
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    app.dependency_overrides[get_document_repository] = lambda: adapter
    app.dependency_overrides[check_database_readiness] = lambda: True
    app.dependency_overrides[get_usage_repository] = lambda: fake_usage_repo
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
