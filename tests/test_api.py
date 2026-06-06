"""Phase 9.1: API integration tests (TestClient)."""

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


def test_api_chat_response_shape() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Which fund is better?"},
    )
    assert response.status_code == 200
    body = response.json()
    for key in ("answer", "last_updated", "is_refusal", "disclaimer"):
        assert key in body


def test_api_schemes_returns_five() -> None:
    response = client.get("/api/schemes")
    assert response.status_code == 200
    schemes = response.json()
    assert len(schemes) == 5
    assert all("source_url" in scheme for scheme in schemes)


def test_api_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "index_ready" in body
