"""Phase 6: RAG + validator integration."""

from datetime import date

from app.classifier import QueryLabel
from app.models import ChunkRecord, RetrievalResult, ScoredChunk, SectionTag, ValidationResult
from app.rag import chat

MID_URL = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
DEFENCE_URL = "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth"


def _chunk(
    slug_prefix: str,
    scheme_name: str,
    url: str,
    section: SectionTag,
    text: str,
    *,
    manager: str | None = None,
) -> ScoredChunk:
    seg = manager and f"fund_management#{manager.lower().replace(' ', '-')}" or f"{section.value}#0"
    return ScoredChunk(
        chunk=ChunkRecord(
            id=f"{slug_prefix}#{seg}",
            text=text,
            scheme_name=scheme_name,
            source_url=url,
            section=section,
            last_updated=date(2026, 6, 2),
            manager_name=manager,
        ),
        score=1.0,
    )


def test_advisory_draft_triggers_refusal() -> None:
    chunks = [
        _chunk(
            "hdfc-mid-cap-fund-direct-growth",
            "HDFC Mid Cap Fund Direct Growth",
            MID_URL,
            SectionTag.EXPENSE_RATIO,
            "Expense ratio: 0.73%",
        )
    ]
    retrieval = RetrievalResult(chunks=chunks)

    def bad_llm(q: str, c: list[ScoredChunk]) -> str:
        return "I recommend you buy this fund immediately."

    response = chat(
        "Expense ratio HDFC Mid Cap",
        retrieve_fn=lambda q: retrieval,
        generate_fn=bad_llm,
    )
    assert response.is_refusal is True


def test_invalid_citation_replaced_by_chunk_url() -> None:
    chunks = [
        _chunk(
            "hdfc-mid-cap-fund-direct-growth",
            "HDFC Mid Cap Fund Direct Growth",
            MID_URL,
            SectionTag.EXPENSE_RATIO,
            "Expense ratio: 0.73%",
        )
    ]
    retrieval = RetrievalResult(chunks=chunks)

    def llm(q: str, c: list[ScoredChunk]) -> str:
        return "The expense ratio is 0.73% per the scheme page."

    response = chat(
        "Expense ratio HDFC Mid Cap",
        retrieve_fn=lambda q: retrieval,
        generate_fn=llm,
    )
    assert str(response.citation_url) == MID_URL


def test_defence_managers_from_chunks() -> None:
    chunks = [
        _chunk(
            "hdfc-defence-fund-direct-growth",
            "HDFC Defence Fund Direct Growth",
            DEFENCE_URL,
            SectionTag.FUND_MANAGEMENT,
            "Priya Ranjan — Fund Manager",
            manager="Priya Ranjan",
        ),
        _chunk(
            "hdfc-defence-fund-direct-growth",
            "HDFC Defence Fund Direct Growth",
            DEFENCE_URL,
            SectionTag.FUND_MANAGEMENT,
            "Dhruv Muchhal — Fund Manager",
            manager="Dhruv Muchhal",
        ),
        _chunk(
            "hdfc-defence-fund-direct-growth",
            "HDFC Defence Fund Direct Growth",
            DEFENCE_URL,
            SectionTag.FUND_MANAGEMENT,
            "Rahul Baijal — Fund Manager",
            manager="Rahul Baijal",
        ),
    ]
    retrieval = RetrievalResult(chunks=chunks, resolved_section=SectionTag.FUND_MANAGEMENT)

    def llm(q: str, c: list[ScoredChunk]) -> str:
        return (
            "Priya Ranjan, Dhruv Muchhal, and Rahul Baijal are listed as fund managers "
            "on the scheme page."
        )

    response = chat(
        "Who manages HDFC Defence Fund?",
        retrieve_fn=lambda q: retrieval,
        generate_fn=llm,
    )
    assert not response.is_refusal
    assert "Priya Ranjan" in response.answer
    assert "Dhruv Muchhal" in response.answer
