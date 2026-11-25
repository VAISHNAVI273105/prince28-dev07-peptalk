"""Unit tests for /v1/chat (streaming & non-streaming) and /v1/usage endpoints."""

from pathlib import Path

from peptalk.llm.gateway import FakeLLM, LLMError, LLMGateway


def test_chat_non_streaming_success(client):
    response = client.post(
        "/v1/chat",
        json={"message": "What is PEP 634?", "stream": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["provider"] == "fake"
    assert data["model"] == "fake-model"
    assert "tokens_in" in data
    assert "tokens_out" in data
    assert "cost_inr" in data
    assert "fallback_used" in data


def test_chat_streaming_success(client):
    response = client.post(
        "/v1/chat",
        json={"message": "What is PEP 634?", "stream": True},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "data:" in response.text
    assert "event: done" in response.text


def test_chat_message_validation_empty(client):
    response = client.post(
        "/v1/chat",
        json={"message": "", "stream": False},
    )
    assert response.status_code == 422


def test_chat_message_validation_too_long(client):
    response = client.post(
        "/v1/chat",
        json={"message": "a" * 4001, "stream": False},
    )
    assert response.status_code == 422


def test_chat_all_models_unavailable_returns_503(client):
    dead_provider = FakeLLM("fake", "fake-model", [LLMError("Dead", retryable=False)])
    client.app.state.gateway = LLMGateway([dead_provider])

    response = client.post(
        "/v1/chat",
        json={"message": "Are you there?", "stream": False},
    )
    assert response.status_code == 503
    assert "No model could answer" in response.json().get("detail", "")


def test_usage_endpoint(client):
    response = client.get("/v1/usage?days=7")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert "total_cost_inr" in data
    assert "calls" in data
    assert len(data["days"]) >= 1
    assert data["calls"] == 1


def test_system_prompt_has_not_sure_rule():
    prompt_path = Path("prompts/chat_system_v1.md")
    assert prompt_path.exists(), "Prompt file prompts/chat_system_v1.md must exist"
    content = prompt_path.read_text(encoding="utf-8")
    assert "I am not sure" in content, (
        "System prompt must contain the 'I am not sure' guideline so the model admits uncertainty"
    )
