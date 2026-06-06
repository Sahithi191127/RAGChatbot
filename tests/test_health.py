"""Phase 0: health endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "mutual-fund-faq-assistant"
    assert "version" in body
    assert body["corpus"]["scheme_count"] == 5
