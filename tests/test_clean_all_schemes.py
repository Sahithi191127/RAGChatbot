"""Verify all five schemes have cleaned processed documents."""

from pathlib import Path

import pytest

from config.loader import get_corpus_config
from ingestion.fetch import fetch_all_schemes
from ingestion.models import FundManagementSection, SectionContent
from ingestion.parse import load_processed_document, parse_all_schemes

PROCESSED = Path("data/processed")


@pytest.fixture(scope="module")
def reprocessed() -> None:
    fetch_all_schemes(use_cache=True)
    parse_all_schemes(write=True)


@pytest.mark.parametrize(
    "slug,min_managers",
    [
        ("hdfc-mid-cap-fund-direct-growth", 2),
        ("hdfc-small-cap-fund-direct-growth", 2),
        ("hdfc-large-cap-fund-direct-growth", 2),
        ("hdfc-gold-etf-fund-of-fund-direct-plan-growth", 2),
        ("hdfc-defence-fund-direct-growth", 3),
    ],
)
def test_scheme_has_core_sections(reprocessed, slug: str, min_managers: int) -> None:
    doc = load_processed_document(slug)
    exit_load = doc.sections["exit_load"]
    expense = doc.sections["expense_ratio"]
    benchmark = doc.sections["benchmark"]
    tax = doc.sections["tax"]
    overview = doc.sections["overview"]
    fm = doc.sections["fund_management"]
    assert isinstance(exit_load, SectionContent) and exit_load.text
    assert isinstance(expense, SectionContent) and "%" in expense.text
    assert isinstance(benchmark, SectionContent) and benchmark.text
    assert isinstance(tax, SectionContent) and tax.text
    assert isinstance(fm, FundManagementSection)
    assert len(fm.managers) >= min_managers
    assert isinstance(overview, SectionContent)
    overview = overview.text
    assert "Vaishnavi Tech Park" not in overview
    assert "Bug Bounty" not in overview


def test_all_five_processed_files_exist(reprocessed) -> None:
    config = get_corpus_config()
    for scheme in config.schemes:
        path = PROCESSED / f"{scheme.slug}.json"
        assert path.is_file(), f"missing {path}"
