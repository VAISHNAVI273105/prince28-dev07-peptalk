
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
