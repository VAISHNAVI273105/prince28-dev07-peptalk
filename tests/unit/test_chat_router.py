"""Unit tests for production question router integration in POST /v1/chat."""

from fastapi.testclient import TestClient

from peptalk.api.deps import check_database_readiness, get_document_repository, get_usage_repository
from peptalk.api.main import create_app
from peptalk.api.routes.chat import OFF_TOPIC_REFUSAL, PERSONAL_REFUSAL
from peptalk.db.repository import DocumentStoreAdapter
from peptalk.llm.gateway import FakeLLM, LLMGateway
from peptalk.store import DocumentStore
from tests.conftest import FakeUsageRepo


def make_test_client(fake_llm: FakeLLM) -> TestClient:
    app = create_app()
    store = DocumentStore("data/sample_records.json")
    adapter = DocumentStoreAdapter(store)

    app.dependency_overrides[get_document_repository] = lambda: adapter
    app.dependency_overrides[check_database_readiness] = lambda: True
    app.dependency_overrides[get_usage_repository] = lambda: FakeUsageRepo()
    app.state.gateway = LLMGateway([fake_llm], usd_inr=95.0)
    return TestClient(app)


def test_chat_routes_personal_question_and_refuses_early():
    # 1st call (router): returns 'personal' -> refuses without second call
    fake = FakeLLM("fake", "fake-model", ["personal"])
    client = make_test_client(fake)

    response = client.post(
        "/v1/chat",
        json={"message": "Why does our deployment fail on the client's server?", "stream": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == PERSONAL_REFUSAL
    assert data["routed"] == "personal"
    # Proves no second LLM call was made:
    assert fake.calls == 1


def test_chat_routes_off_topic_question_and_refuses_early():
    # 1st call (router): returns 'off_topic' -> refuses without second call
    fake = FakeLLM("fake", "fake-model", ["off_topic"])
    client = make_test_client(fake)

    response = client.post(
        "/v1/chat",
        json={"message": "Suggest a name for my pet dog.", "stream": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == OFF_TOPIC_REFUSAL
    assert data["routed"] == "off_topic"
    assert fake.calls == 1


def test_chat_routes_docs_question_and_calls_model():
    # 1st call (router): returns 'docs'
    # 2nd call (generator): answers from documentation
    fake = FakeLLM(
        "fake",
        "fake-model",
        ["docs", "PEP 634 introduced structural pattern matching in Python 3.10."],
    )
    client = make_test_client(fake)

    response = client.post(
        "/v1/chat",
        json={"message": "What is structural pattern matching?", "stream": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "PEP 634" in data["answer"]
    # Proves both calls were made: 1 for routing, 1 for answering
    assert fake.calls == 2


def test_chat_routes_streaming_personal_refusal():
    fake = FakeLLM("fake", "fake-model", ["personal"])
    client = make_test_client(fake)

    response = client.post(
        "/v1/chat",
        json={"message": "Is our database in Singapore or Mumbai?", "stream": True},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert PERSONAL_REFUSAL in response.text
    assert "event: done" in response.text
    assert '"routed": "personal"' in response.text
    assert fake.calls == 1


def test_chat_bypass_router_with_route_false():
    fake = FakeLLM("fake", "fake-model", ["Direct answer without router check."])
    client = make_test_client(fake)

    response = client.post(
        "/v1/chat",
        json={"message": "Any message", "stream": False, "route": False},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Direct answer without router check."
    assert fake.calls == 1
