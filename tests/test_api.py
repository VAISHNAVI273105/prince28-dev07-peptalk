def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_list_documents(client):
    response = client.get("/v1/documents")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_list_documents_pagination(client):
    response = client.get("/v1/documents?limit=2&offset=0")
    assert response.status_code == 200
    assert len(response.json()["items"]) <= 2


def test_get_existing_document(client):
    response = client.get("/v1/documents/pep-0634")
    assert response.status_code == 200
    assert response.json()["id"] == "pep-0634"


def test_get_missing_document(client):
    response = client.get("/v1/documents/999")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_invalid_limit(client):
    response = client.get("/v1/documents?limit=0")
    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_request_id_generated(client):
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_custom_request_id(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "test-request-123"},
    )
    assert response.headers["x-request-id"] == "test-request-123"


def test_processing_time_header(client):
    response = client.get("/health")
    assert "x-process-time-ms" in response.headers


# ---------------------------------------------------------------------------
# Filter and Readiness Tests
# ---------------------------------------------------------------------------


def test_list_documents_filter_by_python_version(client):
    response = client.get("/v1/documents?python_version=3.10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item.get("python_version") == "3.10" for item in data["items"])


def test_list_documents_filter_by_status(client):
    response = client.get("/v1/documents?status=Final")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item.get("status") == "Final" for item in data["items"])


def test_list_documents_filter_by_type(client):
    response = client.get("/v1/documents?type=PEP")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item.get("type") == "PEP" for item in data["items"])


def test_list_documents_filter_by_pep_number(client):
    response = client.get("/v1/documents?pep_number=634")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "pep-0634"


def test_list_documents_invalid_python_version_returns_400(client):
    response = client.get("/v1/documents?python_version=invalid-format")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 400
    assert "Invalid python_version filter" in response.json()["detail"]


def test_list_documents_invalid_status_returns_400(client):
    response = client.get("/v1/documents?status=NotAValidStatus")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 400
    assert "Invalid status filter" in response.json()["detail"]


def test_list_documents_invalid_pep_number_returns_400(client):
    response = client.get("/v1/documents?pep_number=-5")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 400
    assert "pep_number filter must be a positive integer" in response.json()["detail"]


def test_list_documents_empty_type_returns_400(client):
    response = client.get("/v1/documents?type=%20%20")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 400
    assert "type filter cannot be empty" in response.json()["detail"]


def test_readiness_failure_returns_503(client):
    from peptalk.api.deps import check_database_readiness

    client.app.dependency_overrides[check_database_readiness] = lambda: False
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["status"] == 503
    finally:
        client.app.dependency_overrides.pop(check_database_readiness, None)


def test_health_remains_healthy_independent_of_database(client):
    from peptalk.api.deps import check_database_readiness

    # Even if database readiness fails, /health must still succeed
    client.app.dependency_overrides[check_database_readiness] = lambda: False
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    finally:
        client.app.dependency_overrides.pop(check_database_readiness, None)
