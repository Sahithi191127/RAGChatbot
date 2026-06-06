"""Phase 2.3: section-first chunking tests."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models import SectionTag
from config.chunk_ids import build_fund_management_chunk_id, parse_chunk_id
from ingestion.chunk import (
    MAX_CHUNK_CHARS,
    chunk_document,
    format_chunk_text,
    split_text_within_section,
)
from ingestion.models import FundManagementSection, ParsedSchemeDocument, SectionContent
from ingestion.parse import load_processed_document

MID_SLUG = "hdfc-mid-cap-fund-direct-growth"
PROCESSED = Path("data/processed")


@pytest.fixture(scope="module")
def mid_cap_doc() -> ParsedSchemeDocument:
    path = PROCESSED / f"{MID_SLUG}.json"
    if not path.is_file():
        pytest.skip("processed mid cap document missing — run ingestion parse first")
    return load_processed_document(MID_SLUG)


def test_split_single_short_section() -> None:
    parts = split_text_within_section("Exit load of 1% if redeemed within 1 year.")
    assert parts == ["Exit load of 1% if redeemed within 1 year."]


def test_split_long_section_has_overlap() -> None:
    text = "word " * 900
    parts = split_text_within_section(text, max_chars=500, overlap_chars=50)
    assert len(parts) >= 2
    assert all(len(p) <= 500 for p in parts)


def test_format_chunk_text_includes_scheme_and_section() -> None:
    text = format_chunk_text(
        scheme_name="HDFC Mid Cap Fund Direct Growth",
        section=SectionTag.EXPENSE_RATIO,
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        body="Expense ratio: 0.73%",
    )
    assert "Scheme: HDFC Mid Cap Fund Direct Growth" in text
    assert "Section: expense_ratio" in text
    assert "0.73%" in text


def test_chunk_document_one_per_manager(mid_cap_doc: ParsedSchemeDocument) -> None:
    chunks = chunk_document(mid_cap_doc)
    fm_chunks = [c for c in chunks if c.section == SectionTag.FUND_MANAGEMENT]
    assert len(fm_chunks) >= 2
    for chunk in fm_chunks:
        assert chunk.manager_name
        assert "Education:" in chunk.text or "Fund Manager" in chunk.text
        parsed = parse_chunk_id(chunk.id)
        assert parsed["section"] == "fund_management"
        assert parsed["segment"] != "0"


def test_chunk_document_core_sections(mid_cap_doc: ParsedSchemeDocument) -> None:
    chunks = chunk_document(mid_cap_doc)
    sections = {c.section for c in chunks}
    assert SectionTag.EXPENSE_RATIO in sections
    assert SectionTag.EXIT_LOAD in sections
    assert SectionTag.BENCHMARK in sections
    assert SectionTag.MINIMUM_INVESTMENT in sections


def test_expense_ratio_chunk_id(mid_cap_doc: ParsedSchemeDocument) -> None:
    chunks = chunk_document(mid_cap_doc)
    expense = next(c for c in chunks if c.section == SectionTag.EXPENSE_RATIO)
    assert expense.id == f"{MID_SLUG}#expense_ratio#0"
    assert "%" in expense.text


def test_fund_management_chunk_id_stable() -> None:
    chunk_id = build_fund_management_chunk_id(MID_SLUG, "Dhruv Muchhal")
    assert chunk_id == f"{MID_SLUG}#fund_management#dhruv-muchhal"


def test_chunk_all_five_when_processed() -> None:
    if not PROCESSED.exists():
        pytest.skip("no processed data")
    slugs = list(PROCESSED.glob("*.json"))
    slugs = [p for p in slugs if not p.name.endswith(".chunks.json")]
    if len(slugs) < 5:
        pytest.skip("need 5 processed scheme files")
    from ingestion.chunk import chunk_all_schemes

    chunks = chunk_all_schemes(write=False)
    assert 40 <= len(chunks) <= 120
    by_scheme = {c.id.split("#")[0] for c in chunks}
    assert len(by_scheme) == 5


def test_oversized_section_splits_into_multiple_chunks() -> None:
    now = datetime.now(timezone.utc)
    long_body = "A" * (MAX_CHUNK_CHARS + 500)
    doc = ParsedSchemeDocument(
        slug="test-scheme",
        scheme_name="Test Scheme",
        source_url="https://groww.in/mutual-funds/test-scheme",
        category="Equity",
        fetch_timestamp=now,
        parsed_at=now,
        sections={
            SectionTag.OVERVIEW.value: SectionContent(text=long_body),
            SectionTag.FUND_MANAGEMENT.value: FundManagementSection(managers=[]),
        },
    )
    chunks = chunk_document(doc)
    overview = [c for c in chunks if c.section == SectionTag.OVERVIEW]
    assert len(overview) >= 2
    assert overview[0].id.endswith("#0")
    assert overview[1].id.endswith("#1")
