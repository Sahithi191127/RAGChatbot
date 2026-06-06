"""Phase 9: acceptance tests mirroring the manual QA matrix."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import reset_rate_limit_state
from config.loader import get_corpus_config, get_refusal_citation_allowlist

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


@pytest.fixture(scope="module")
def requires_index() -> None:
    from app.retriever import index_is_ready

    if not index_is_ready():
        pytest.skip("Chroma index not built")


def _chat(message: str) -> dict:
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "scheme_name,slug",
    [
        ("HDFC Mid Cap Fund Direct Growth", "hdfc-mid-cap-fund-direct-growth"),
        ("HDFC Small Cap Fund Direct Growth", "hdfc-small-cap-fund-direct-growth"),
        ("HDFC Large Cap Fund Direct Growth", "hdfc-large-cap-fund-direct-growth"),
        (
            "HDFC Gold ETF Fund of Fund Direct Plan Growth",
            "hdfc-gold-etf-fund-of-fund-direct-plan-growth",
        ),
        ("HDFC Defence Fund Direct Growth", "hdfc-defence-fund-direct-growth"),
    ],
)
def test_expense_ratio_each_scheme(requires_index, scheme_name: str, slug: str) -> None:
    body = _chat(f"What is the expense ratio of {scheme_name}?")
    assert body["is_refusal"] is False
    assert slug in body["citation_url"]
    assert "expense" in body["answer"].lower() or "%" in body["answer"]


def test_exit_load_defence(requires_index) -> None:
    body = _chat("What is the exit load on HDFC Defence Fund Direct Growth?")
    assert body["is_refusal"] is False
    assert "hdfc-defence-fund-direct-growth" in body["citation_url"]
    assert "exit load" in body["answer"].lower() or "1%" in body["answer"]


def test_min_sip_mid_cap(requires_index) -> None:
    body = _chat("What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?")
    assert body["is_refusal"] is False
    assert "hdfc-mid-cap-fund-direct-growth" in body["citation_url"]
    assert "minimum" in body["answer"].lower() or "sip" in body["answer"].lower()


def test_benchmark_large_cap(requires_index) -> None:
    body = _chat("What is the benchmark of HDFC Large Cap Fund Direct Growth?")
    assert body["is_refusal"] is False
    assert "hdfc-large-cap-fund-direct-growth" in body["citation_url"]
    assert "benchmark" in body["answer"].lower()


def test_gold_etf_fof_managers(requires_index) -> None:
    body = _chat("Who manages HDFC Gold ETF Fund of Fund Direct Plan Growth?")
    assert body["is_refusal"] is False
    assert "managed by" in body["answer"].lower() or "manager" in body["answer"].lower()


def test_defence_managers(requires_index) -> None:
    body = _chat("Who manages HDFC Defence Fund Direct Growth?")
    assert body["is_refusal"] is False
    for name in ("Priya Ranjan", "Dhruv Muchhal", "Rahul Baijal"):
        assert name in body["answer"]


def test_advisory_refusal() -> None:
    body = _chat("Should I invest in HDFC Mid Cap?")
    assert body["is_refusal"] is True
    assert body["citation_url"] in get_refusal_citation_allowlist()
    assert "investment advice" in body["answer"].lower()


def test_comparison_refusal() -> None:
    body = _chat("Which fund is better?")
    assert body["is_refusal"] is True
    assert body["citation_url"] in get_refusal_citation_allowlist()


def test_performance_refusal() -> None:
    body = _chat("Compare 3Y returns of all HDFC funds")
    assert body["is_refusal"] is True


def test_unsupported_scheme_sbi() -> None:
    body = _chat("SBI Mid Cap expense ratio")
    assert body["is_refusal"] is True
    assert "five HDFC mutual fund schemes" in body["answer"]
    config = get_corpus_config()
    for scheme in config.schemes:
        assert scheme.scheme_name in body["answer"]


def test_unrelated_weather() -> None:
    body = _chat("What is the weather in Mumbai?")
    assert body["is_refusal"] is True
    assert "don't know" in body["answer"].lower()
    assert "Gold ETF" not in body["answer"]


def test_pan_rejected() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "My PAN is ABCDE1234F, what is the expense ratio?"},
    )
    assert response.status_code == 400
    assert "personal identifiers" in response.json()["detail"].lower()
