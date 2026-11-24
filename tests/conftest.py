import os

import pytest
from fastapi.testclient import TestClient

# Ensure safe default environment for tests in clean clones / CI
os.environ.setdefault("APP_ENV", "ci")

from peptalk.api.deps import check_database_readiness, get_document_repository
from peptalk.api.main import create_app
from peptalk.db.repository import DocumentStoreAdapter
from peptalk.store import DocumentStore


@pytest.fixture
def client():
    app = create_app()
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    app.dependency_overrides[get_document_repository] = lambda: adapter
    app.dependency_overrides[check_database_readiness] = lambda: True

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
