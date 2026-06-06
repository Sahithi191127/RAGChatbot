"""Phase 6: validator tests."""

from datetime import date

from app.models import ChunkRecord, ScoredChunk, SectionTag
from app.validator import sanitize_draft, validate_draft

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


def test_validate_passes_grounded_expense() -> None:
    chunks = [
        _chunk(
            SectionTag.EXPENSE_RATIO,
            "Scheme: HDFC Mid Cap\n\nExpense ratio: 0.73%",
        )
    ]
    result = validate_draft("The expense ratio is 0.73% on the scheme page.", chunks)
    assert result.passed
    assert result.suggested_citation_url == MID_URL


def test_validate_refuses_advisory_draft() -> None:
    chunks = [_chunk(SectionTag.EXPENSE_RATIO, "Expense ratio: 0.73%")]
    result = validate_draft("I recommend you buy this fund now.", chunks)
    assert result.should_refuse
    assert not result.passed


def test_validate_fails_ungrounded_percentage() -> None:
    chunks = [_chunk(SectionTag.EXPENSE_RATIO, "Expense ratio: 0.73%")]
    result = validate_draft("The expense ratio is 1.25%.", chunks)
    assert not result.passed
    assert any("ungrounded_percentage" in issue for issue in result.issues)


def test_validate_fund_management_requires_known_manager() -> None:
    chunks = [
        _chunk(
            SectionTag.FUND_MANAGEMENT,
            "Manager: Dhruv Muchhal\n\nDhruv Muchhal — Fund Manager",
            manager="Dhruv Muchhal",
        )
    ]
    bad = validate_draft(
        "The fund is managed by Priya Ranjan according to the page.",
        chunks,
    )
    assert not bad.passed

    good = validate_draft(
        "Dhruv Muchhal is listed as a fund manager on the scheme page.",
        chunks,
    )
    assert good.passed


def test_validate_fails_performance_not_in_context() -> None:
    chunks = [_chunk(SectionTag.OVERVIEW, "NAV and AUM only.")]
    result = validate_draft("The fund will return +22% over 3 years.", chunks)
    assert not result.passed


def test_sanitize_strips_urls_and_truncates() -> None:
    text = "See https://evil.com/x. One. Two. Three. Four."
    clean = sanitize_draft(text)
    assert "http" not in clean
    assert clean.count(".") <= 3
