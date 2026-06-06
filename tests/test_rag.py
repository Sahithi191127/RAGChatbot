"""Phase 5.4: RAG orchestrator tests."""

from __future__ import annotations

from datetime import date

import pytest

from app.classifier import QueryLabel
from app.models import ChunkRecord, RetrievalResult, ScoredChunk, SectionTag
from app.rag import chat

MID_URL = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"


def _chunk(section: SectionTag, text: str, *, manager: str | None = None) -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            id=f"hdfc-mid-cap-fund-direct-growth#{section.value}#0",
            text=text,
            scheme_name="HDFC Mid Cap Fund Direct Growth",
            source_url=MID_URL,
            section=section,
            last_updated=date(2026, 6, 2),
            manager_name=manager,
        ),
        score=1.0,
    )


def test_should_i_invest_refusal_no_retriever() -> None:
    called = False

    def fake_retrieve(query: str) -> RetrievalResult:
        nonlocal called
        called = True
        return RetrievalResult()

    response = chat("Should I invest?", retrieve_fn=fake_retrieve)
    assert response.is_refusal is True
    assert called is False


def test_which_fund_better_refusal() -> None:
    response = chat("Which fund is better?", retrieve_fn=lambda q: RetrievalResult())
    assert response.is_refusal is True


def test_returns_question_performance_refusal() -> None:
    response = chat("What returns will I get?", retrieve_fn=lambda q: RetrievalResult())
    assert response.is_refusal is True


def test_unsupported_scheme_sbi_lists_schemes() -> None:
    response = chat("SBI Mid Cap expense ratio", retrieve_fn=lambda q: RetrievalResult())
    assert response.is_refusal is True
    assert "five HDFC mutual fund schemes" in response.answer
    called = False

    def fake_retrieve(query: str) -> RetrievalResult:
        nonlocal called
        called = True
        return RetrievalResult()

    chat("SBI Mid Cap expense ratio", retrieve_fn=fake_retrieve)
    assert called is False


def test_unrelated_weather_no_scheme_list() -> None:
    response = chat("What is the weather today?", retrieve_fn=lambda q: RetrievalResult())
    assert response.is_refusal is True
    assert "I don't know that information" in response.answer
    assert "five HDFC mutual fund schemes" not in response.answer.split("Examples")[0]


def test_unrelated_my_name_no_retriever() -> None:
    called = False

    def fake_retrieve(query: str) -> RetrievalResult:
        nonlocal called
        called = True
        return RetrievalResult()

    response = chat("What is my name?", retrieve_fn=fake_retrieve)
    assert response.is_refusal is True
    assert called is False


@pytest.fixture
def requires_index() -> None:
    from app.retriever import index_is_ready

    if not index_is_ready():
        pytest.skip("Chroma index required")


def test_factual_expense_mid_cap(requires_index) -> None:
    response = chat("Expense ratio HDFC Mid Cap")
    assert response.is_refusal is False
    assert str(response.citation_url) == MID_URL
    assert "%" in response.answer or "expense" in response.answer.lower()
    assert response.disclaimer


def test_factual_with_stub_chunks() -> None:
    chunks = [
        _chunk(
            SectionTag.EXPENSE_RATIO,
            "Scheme: HDFC Mid Cap Fund Direct Growth\nSection: expense_ratio\n\nExpense ratio: 0.73%",
        )
    ]
    retrieval = RetrievalResult(
        chunks=chunks,
        resolved_slug="hdfc-mid-cap-fund-direct-growth",
        resolved_section=SectionTag.EXPENSE_RATIO,
    )
    response = chat("Expense ratio HDFC Mid Cap", retrieve_fn=lambda q: retrieval)
    assert response.is_refusal is False
    assert "0.73%" in response.answer
