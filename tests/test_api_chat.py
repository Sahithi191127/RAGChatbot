"""Phase 7: Chat API integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import reset_rate_limit_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_LLM_STUB", "true")
    monkeypatch.setenv("LLM_API_KEY", "")
    from app.settings import get_settings

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_rate_limits() -> None:
    reset_rate_limit_state()


@pytest.fixture
def requires_index() -> None:
    from app.retriever import index_is_ready

    if not index_is_ready():
        pytest.skip("Chroma index not built")


def test_chat_factual_expense_ratio(requires_index) -> None:
    response = client.post(
        "/api/chat",
        json={"message": "What is the expense ratio of HDFC Mid Cap Fund Direct Growth?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_refusal"] is False
    assert "citation_url" in body
    assert "last_updated" in body
    assert body["disclaimer"]
    assert "expense" in body["answer"].lower() or "%" in body["answer"]


def test_chat_refusal_advisory() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Should I invest in HDFC Defence Fund?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_refusal"] is True
    assert "amfi" in body["citation_url"].lower() or "sebi" in body["citation_url"].lower()


def test_chat_refusal_comparison() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Which fund is better?"},
    )
    assert response.status_code == 200
    assert response.json()["is_refusal"] is True


def test_chat_unsupported_scheme_sbi() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "SBI Mid Cap expense ratio"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_refusal"] is True
    assert "five HDFC mutual fund schemes" in body["answer"]


def test_chat_unrelated_weather() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "What is the weather in Mumbai?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_refusal"] is True
    assert "don't know" in body["answer"].lower()
    assert "Gold ETF" not in body["answer"]


def test_chat_rejects_pan() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "My PAN is ABCDE1234F, what is the expense ratio?"},
    )
    assert response.status_code == 400
    assert "personal identifiers" in response.json()["detail"].lower()


def test_chat_rejects_empty_message() -> None:
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 422


def test_chat_ignores_extra_fields() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Expense ratio HDFC Mid Cap", "user_id": "secret"},
    )
    assert response.status_code == 200


def test_list_schemes() -> None:
    response = client.get("/api/schemes")
    assert response.status_code == 200
    schemes = response.json()
    assert len(schemes) == 5
    assert schemes[0]["slug"]
    assert schemes[0]["scheme_name"]


def test_health_includes_index_ready() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "index_ready" in response.json()


def test_rate_limit_returns_429() -> None:
    from fastapi import FastAPI

    from app.rate_limit import RateLimitMiddleware, reset_rate_limit_state

    reset_rate_limit_state()
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, limit=2, window_seconds=60)

    @test_app.post("/api/chat")
    def _dummy_chat() -> dict:
        return {"ok": True}

    test_client = TestClient(test_app)
    payload = {"message": "Which fund is better?"}
    assert test_client.post("/api/chat", json=payload).status_code == 200
    assert test_client.post("/api/chat", json=payload).status_code == 200
    assert test_client.post("/api/chat", json=payload).status_code == 429
