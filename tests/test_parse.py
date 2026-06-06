"""Phase 2.2: ingestion parse tests."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models import SectionTag
from config.loader import clear_corpus_cache, get_scheme_by_slug
from ingestion.fetch import fetch_scheme
from ingestion.models import FundManagementSection
from ingestion.parse import load_processed_document, parse_content, parse_scheme
from ingestion.paths import CACHE_DIR, PROCESSED_DIR, processed_json_path

FIXTURE_MD = (
    Path(__file__).parent / "fixtures" / "hdfc-mid-cap-fund-direct-growth.md"
)
SLUG = "hdfc-mid-cap-fund-direct-growth"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_corpus_cache()
    yield
    clear_corpus_cache()


@pytest.fixture
def scheme():
    found = get_scheme_by_slug(SLUG)
    assert found is not None
    return found


@pytest.fixture
def fetched_scheme(monkeypatch, scheme) -> None:
    monkeypatch.setenv("USE_CACHE", "true")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_markdown = CACHE_DIR / f"{SLUG}.md"
    cache_markdown.write_text(FIXTURE_MD.read_text(encoding="utf-8"), encoding="utf-8")
    result = fetch_scheme(scheme, use_cache=True)
    assert result.success


def test_parse_content_extracts_sections(scheme) -> None:
    content = FIXTURE_MD.read_text(encoding="utf-8")
    document = parse_content(
        content,
        scheme,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        content_type="markdown",
    )

    assert "0.73%" in document.section_text(SectionTag.EXPENSE_RATIO)
    assert "Exit load of 1%" in document.section_text(SectionTag.EXIT_LOAD)
    assert "₹100" in document.section_text(SectionTag.MINIMUM_INVESTMENT)
    assert "NIFTY Midcap 150" in document.section_text(SectionTag.BENCHMARK)
    assert "taxed at 20%" in document.section_text(SectionTag.TAX)

    fm = document.sections[SectionTag.FUND_MANAGEMENT.value]
    assert isinstance(fm, FundManagementSection)
    assert len(fm.managers) >= 2
    names = {m.name for m in fm.managers}
    assert "Chirag Setalvad" in names
    assert "Dhruv Muchhal" in names
    assert any("B. Sc and MBA" in m.education for m in fm.managers)


def test_parse_scheme_writes_json(fetched_scheme) -> None:
    document = parse_scheme(SLUG, write=True)
    path = processed_json_path(SLUG)
    assert path.is_file()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["slug"] == SLUG
    assert "fund_management" in payload["sections"]

    loaded = load_processed_document(SLUG)
    assert loaded.scheme_name == document.scheme_name


def test_parse_html_minimal(scheme) -> None:
    html = """
    <html><body>
    <h1>HDFC Mid Cap Fund Direct Growth</h1>
    <p>Expense ratio</p><p>0.73%</p>
    <h3>Fund management</h3>
    <p>CS</p><p>Chirag Setalvad</p><p>Jan 2013 - Present</p>
    <h4>Education</h4><p>MBA from UNC.</p>
    </body></html>
    """
    document = parse_content(
        html,
        scheme,
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        content_type="html",
    )
    assert "0.73%" in document.section_text(SectionTag.EXPENSE_RATIO) or document.section_text(
        SectionTag.OVERVIEW
    )
